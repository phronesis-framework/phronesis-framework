"""Tests for :meth:`Agent.stream`."""

from __future__ import annotations

from collections.abc import AsyncIterator, Sequence

import pytest

from phronesis.agents.agent import Agent
from phronesis.agents.events import (
    AgentEvent,
    RunCompleted,
    RunFailed,
    RunStarted,
    TextDelta,
    ToolCallCompleted,
    ToolCallStarted,
)
from phronesis.agents.id import AgentId
from phronesis.agents.run import RunRequest
from phronesis.agents.spec import AgentSpec
from phronesis.core.messages import Message
from phronesis.providers.chunks import LLMChunk
from phronesis.providers.protocol import ProviderFeature
from phronesis.providers.types import LLMRequest, LLMResponse, ToolCall


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

    def count_tokens(self, messages: Sequence[Message]) -> int:
        return 0


def _spec(provider: object) -> AgentSpec:
    return AgentSpec(
        id=AgentId("phronesis.agents.x"),
        name="x",
        model=provider,  # type: ignore[arg-type]
        system_prompt="hi",
    )


async def _collect(it: AsyncIterator[AgentEvent]) -> list[AgentEvent]:
    return [e async for e in it]


class TestStreamSuccessfulRun:
    @pytest.mark.asyncio
    async def test_first_event_is_run_started(self) -> None:
        provider = _StubProvider([LLMResponse(text="hello", finish_reason="stop")])
        agent = Agent(_spec(provider))

        events = await _collect(agent.stream("hi"))

        assert isinstance(events[0], RunStarted)
        assert events[0].agent_id.canonical == "phronesis.agents.x"

    @pytest.mark.asyncio
    async def test_last_event_is_run_completed(self) -> None:
        provider = _StubProvider([LLMResponse(text="hello", finish_reason="stop")])
        agent = Agent(_spec(provider))

        events = await _collect(agent.stream("hi"))

        assert isinstance(events[-1], RunCompleted)
        assert events[-1].result.success is True
        assert events[-1].result.output == "hello"

    @pytest.mark.asyncio
    async def test_emits_text_delta(self) -> None:
        provider = _StubProvider([LLMResponse(text="hello", finish_reason="stop")])
        agent = Agent(_spec(provider))

        events = await _collect(agent.stream("hi"))
        deltas = [e for e in events if isinstance(e, TextDelta)]

        assert any(d.text == "hello" for d in deltas)


class TestStreamMaxIterations:
    @pytest.mark.asyncio
    async def test_emits_run_failed(self) -> None:
        provider = _StubProvider(
            [
                LLMResponse(
                    finish_reason="tool_use",
                    tool_calls=(ToolCall(call_id="t1", tool_name="ghost", arguments={}),),
                ),
            ]
            * 5,
        )
        spec = AgentSpec(
            id=AgentId("phronesis.agents.x"),
            name="x",
            model=provider,  # type: ignore[arg-type]
            system_prompt="hi",
            max_iterations=2,
        )
        agent = Agent(spec)

        events = await _collect(agent.stream("hi"))

        assert isinstance(events[-1], RunFailed)


class TestStreamToolCallEvents:
    @pytest.mark.asyncio
    async def test_emits_started_and_completed_for_unknown_tool(self) -> None:
        provider = _StubProvider(
            [
                LLMResponse(
                    finish_reason="tool_use",
                    tool_calls=(ToolCall(call_id="t1", tool_name="ghost", arguments={}),),
                ),
                LLMResponse(text="done", finish_reason="stop"),
            ],
        )
        agent = Agent(_spec(provider))

        events = await _collect(agent.stream("hi"))

        started = [e for e in events if isinstance(e, ToolCallStarted)]
        completed = [e for e in events if isinstance(e, ToolCallCompleted)]

        assert len(started) == 1
        assert started[0].tool_name == "ghost"
        assert len(completed) == 1
        assert completed[0].is_error is True


class TestStreamAcceptsRunRequest:
    @pytest.mark.asyncio
    async def test_request_overrides_input(self) -> None:
        provider = _StubProvider([LLMResponse(text="ok", finish_reason="stop")])
        agent = Agent(_spec(provider))

        events = await _collect(agent.stream(RunRequest(input="explicit")))

        assert isinstance(events[-1], RunCompleted)
