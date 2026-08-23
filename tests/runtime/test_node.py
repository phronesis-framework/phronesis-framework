"""Tests for node adapters: callable_node, agent_node, as_node."""

from __future__ import annotations

import asyncio
import time
from collections.abc import AsyncIterator, Sequence
from typing import Any

import pytest

from phronesis.agents import Agent, AgentSpec, RunRequest
from phronesis.agents.errors import AgentMaxIterationsError, AgentTimeoutError
from phronesis.agents.id import AgentId
from phronesis.core.messages import Message
from phronesis.providers.chunks import LLMChunk
from phronesis.providers.protocol import ProviderFeature
from phronesis.providers.types import LLMRequest, LLMResponse, ToolCall
from phronesis.runtime import (
    CancelledError,
    ExecutionContext,
    RunOutcome,
    agent_node,
    as_node,
    callable_node,
)


class TestCallableNode:
    async def test_two_arg_callable(self, root_ctx: ExecutionContext) -> None:
        async def fn(ctx: ExecutionContext, value: Any) -> str:
            assert ctx is root_ctx
            return f"got:{value}"

        node = callable_node(fn)
        outcome = await node(root_ctx, "hi")

        assert outcome.success
        assert outcome.output == "got:hi"

    async def test_one_arg_callable(self, root_ctx: ExecutionContext) -> None:
        async def fn(value: Any) -> str:
            return str(value).upper()

        node = callable_node(fn)
        outcome = await node(root_ctx, "hi")

        assert outcome.output == "HI"

    async def test_callable_raising_yields_fail_outcome(self, root_ctx: ExecutionContext) -> None:
        async def fn(_v: Any) -> None:
            raise ValueError("boom")

        node = callable_node(fn)
        outcome = await node(root_ctx, None)

        assert not outcome.success
        assert isinstance(outcome.error, ValueError)

    async def test_callable_returning_outcome_passes_through(
        self, root_ctx: ExecutionContext
    ) -> None:
        original = RunOutcome.ok(output="explicit")

        async def fn(_v: Any) -> RunOutcome:
            return original

        node = callable_node(fn)
        outcome = await node(root_ctx, None)

        assert outcome is original


class TestAsNode:
    async def test_async_function_becomes_callable_node(self, root_ctx: ExecutionContext) -> None:
        async def fn(value: Any) -> str:
            return str(value)

        node = as_node(fn)
        outcome = await node(root_ctx, 7)

        assert outcome.output == "7"

    def test_unsupported_raises(self) -> None:
        with pytest.raises(TypeError):
            as_node(123)


class _SlowProvider:
    """Provider whose completion takes ``delay`` seconds."""

    def __init__(self, delay: float) -> None:
        self._delay = delay
        self.calls = 0

    async def complete(self, _request: LLMRequest) -> LLMResponse:
        self.calls += 1
        await asyncio.sleep(self._delay)

        return LLMResponse(text="late", finish_reason="stop")

    def stream(self, _request: LLMRequest) -> AsyncIterator[LLMChunk]:
        async def _empty() -> AsyncIterator[LLMChunk]:
            return
            yield  # pragma: no cover - empty async generator

        return _empty()

    def supports(self, _feature: ProviderFeature) -> bool:
        return False

    def context_window_size(self) -> int:
        return 200_000

    def count_tokens(self, _messages: Sequence[Message]) -> int:
        return 0

    async def count_tokens_exact(self, _messages: Sequence[Message]) -> int | None:
        return None


def _slow_agent(delay: float) -> Agent:
    return Agent(
        AgentSpec(
            id=AgentId("phronesis.runtime.test_node.slow"),
            name="slow",
            model=_SlowProvider(delay),
            system_prompt="slow",
        ),
    )


class TestAgentNodeHonoursRunBudget:
    async def test_deadline_aborts_the_agent(self) -> None:
        node = agent_node(_slow_agent(delay=1.0))
        ctx = ExecutionContext.new(deadline_s=0.05)

        started = time.monotonic()
        outcome = await node(ctx, "hi")
        elapsed = time.monotonic() - started

        assert not outcome.success
        assert isinstance(outcome.error, AgentTimeoutError)
        assert elapsed < 0.5

    async def test_cancellation_mid_run_aborts_the_agent(self) -> None:
        node = agent_node(_slow_agent(delay=1.0))
        ctx = ExecutionContext.new()

        async def cancel_soon() -> None:
            await asyncio.sleep(0.05)
            ctx.cancel()

        started = time.monotonic()
        _, outcome = await asyncio.gather(cancel_soon(), node(ctx, "hi"))
        elapsed = time.monotonic() - started

        assert not outcome.success
        assert isinstance(outcome.error, CancelledError)
        assert elapsed < 0.5

    async def test_already_cancelled_context_never_calls_the_provider(self) -> None:
        agent = _slow_agent(delay=1.0)
        ctx = ExecutionContext.new()
        ctx.cancel()

        outcome = await agent_node(agent)(ctx, "hi")

        assert not outcome.success
        assert isinstance(outcome.error, CancelledError)
        assert agent.spec.model.calls == 0  # type: ignore[attr-defined]

    async def test_request_timeout_wins_when_tighter_than_deadline(self) -> None:
        node = agent_node(_slow_agent(delay=1.0))
        ctx = ExecutionContext.new(deadline_s=10.0)

        started = time.monotonic()
        outcome = await node(ctx, RunRequest(input="hi", timeout_seconds=0.05))
        elapsed = time.monotonic() - started

        assert not outcome.success
        assert elapsed < 0.5

    async def test_no_deadline_leaves_the_request_untouched(self) -> None:
        node = agent_node(_slow_agent(delay=0.0))
        ctx = ExecutionContext.new()

        outcome = await node(ctx, "hi")

        assert outcome.success
        assert outcome.output == "late"

    async def test_agent_error_becomes_a_failed_outcome(self) -> None:
        agent = Agent(
            AgentSpec(
                id=AgentId("phronesis.runtime.test_node.capped"),
                name="capped",
                model=_LoopingProvider(),
                system_prompt="loops",
                max_iterations=1,
            ),
        )

        outcome = await agent_node(agent)(ExecutionContext.new(), "hi")

        assert not outcome.success
        assert isinstance(outcome.error, AgentMaxIterationsError)


class _LoopingProvider(_SlowProvider):
    """Provider that always asks for a tool call, so the loop never settles."""

    def __init__(self) -> None:
        super().__init__(delay=0.0)

    async def complete(self, _request: LLMRequest) -> LLMResponse:
        self.calls += 1

        return LLMResponse(
            text="",
            tool_calls=(ToolCall(call_id="c1", tool_name="missing", arguments={}),),
            finish_reason="tool_use",
        )
