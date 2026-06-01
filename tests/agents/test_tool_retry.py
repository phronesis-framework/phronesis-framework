"""Tests for tool retry policy honoured by the agent loop."""

from __future__ import annotations

from collections.abc import AsyncIterator, Sequence

import pytest

from phronesis.agents.agent import Agent
from phronesis.agents.id import AgentId
from phronesis.agents.spec import AgentSpec
from phronesis.providers.chunks import LLMChunk
from phronesis.providers.protocol import ProviderFeature
from phronesis.providers.types import LLMRequest, LLMResponse, ToolCall
from phronesis.tools.decorator import tool
from phronesis.tools.errors import ToolError
from phronesis.tools.retry import RetryPolicy


class _StubProvider:
    def __init__(self, responses: list[LLMResponse]) -> None:
        self._responses = list(responses)

    async def complete(self, request: LLMRequest) -> LLMResponse:
        return self._responses.pop(0)

    def stream(self, request: LLMRequest) -> AsyncIterator[LLMChunk]:
        async def _empty() -> AsyncIterator[LLMChunk]:
            return
            yield  # pragma: no cover

        return _empty()

    def supports(self, feature: ProviderFeature) -> bool:
        return False

    def context_window_size(self) -> int:
        return 200_000

    def count_tokens(self, messages: Sequence[object]) -> int:
        return 0


class _FlakyError(ToolError):
    pass


class TestToolRetryInLoop:
    @pytest.mark.asyncio
    async def test_retries_until_success(self) -> None:
        call_count = {"n": 0}

        @tool(
            id="phronesis.tests.flaky_success",
            retry=RetryPolicy(max_attempts=3),
        )
        def flaky() -> str:
            call_count["n"] += 1

            if call_count["n"] < 3:
                raise _FlakyError("transient", details={})

            return "ok"

        provider = _StubProvider(
            [
                LLMResponse(
                    finish_reason="tool_use",
                    tool_calls=(ToolCall(call_id="t1", tool_name="flaky", arguments={}),),
                ),
                LLMResponse(text="done", finish_reason="stop"),
            ],
        )
        spec = AgentSpec(
            id=AgentId("phronesis.agents.x"),
            name="x",
            model=provider,  # type: ignore[arg-type]
            system_prompt="hi",
            tools=(flaky,),
        )
        agent = Agent(spec)

        result = await agent.run("hi")

        assert result.success is True
        assert call_count["n"] == 3

    @pytest.mark.asyncio
    async def test_exhausts_attempts_and_propagates(self) -> None:
        call_count = {"n": 0}

        @tool(
            id="phronesis.tests.flaky_fail",
            retry=RetryPolicy(max_attempts=2),
        )
        def always_fail() -> str:
            call_count["n"] += 1
            raise _FlakyError("boom", details={})

        provider = _StubProvider(
            [
                LLMResponse(
                    finish_reason="tool_use",
                    tool_calls=(ToolCall(call_id="t1", tool_name="always_fail", arguments={}),),
                ),
                LLMResponse(text="done", finish_reason="stop"),
            ],
        )
        spec = AgentSpec(
            id=AgentId("phronesis.agents.x"),
            name="x",
            model=provider,  # type: ignore[arg-type]
            system_prompt="hi",
            tools=(always_fail,),
        )
        agent = Agent(spec)

        result = await agent.run("hi")

        assert call_count["n"] == 2
        assert result.success is True
        tool_blocks = [b for m in result.messages for b in getattr(m, "content", ())]
        errors = [b for b in tool_blocks if getattr(b, "is_error", False)]
        assert len(errors) == 1

    @pytest.mark.asyncio
    async def test_no_retry_by_default(self) -> None:
        call_count = {"n": 0}

        @tool(id="phronesis.tests.no_retry_default")
        def once() -> str:
            call_count["n"] += 1
            raise _FlakyError("boom", details={})

        provider = _StubProvider(
            [
                LLMResponse(
                    finish_reason="tool_use",
                    tool_calls=(ToolCall(call_id="t1", tool_name="once", arguments={}),),
                ),
                LLMResponse(text="done", finish_reason="stop"),
            ],
        )
        spec = AgentSpec(
            id=AgentId("phronesis.agents.x"),
            name="x",
            model=provider,  # type: ignore[arg-type]
            system_prompt="hi",
            tools=(once,),
        )
        agent = Agent(spec)

        await agent.run("hi")

        assert call_count["n"] == 1
