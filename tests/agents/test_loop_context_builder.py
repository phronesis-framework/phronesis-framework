"""Integration tests for :class:`ContextBuilder` inside the agent loop."""

from __future__ import annotations

from collections.abc import AsyncIterator, Sequence

import pytest

from phronesis.agents.id import AgentId
from phronesis.agents.loop import run_loop
from phronesis.agents.run import RunRequest
from phronesis.agents.spec import AgentSpec
from phronesis.context.default import DefaultContextBuilder
from phronesis.context.input import BuildInput
from phronesis.core.messages import (
    AssistantMessage,
    Message,
    SystemMessage,
    TextBlock,
    UserMessage,
)
from phronesis.providers.chunks import LLMChunk
from phronesis.providers.protocol import ProviderFeature
from phronesis.providers.types import LLMRequest, LLMResponse


class _RecordingProvider:
    def __init__(self, responses: list[LLMResponse]) -> None:
        self._responses = list(responses)
        self.requests: list[LLMRequest] = []

    async def complete(self, request: LLMRequest) -> LLMResponse:
        self.requests.append(request)

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

    async def count_tokens_exact(self, messages: Sequence[Message]) -> int | None:
        return None


class _RecordingBuilder:
    def __init__(self) -> None:
        self.calls: list[BuildInput] = []
        self._delegate = DefaultContextBuilder()

    async def build(self, input: BuildInput) -> list[Message]:
        self.calls.append(input)

        return await self._delegate.build(input)


class _CustomPrefixBuilder:
    async def build(self, input: BuildInput) -> list[Message]:
        messages: list[Message] = []
        history_starts_with_system = bool(input.history) and isinstance(
            input.history[0], SystemMessage
        )

        if input.system_prompt and not history_starts_with_system:
            messages.append(SystemMessage(content=(TextBlock(text=input.system_prompt),)))

        messages.extend(input.history)
        messages.append(AssistantMessage(content=(TextBlock(text="<<builder-marker>>"),)))

        if input.new_input is not None:
            messages.append(input.new_input)

        return messages


def _spec(provider: _RecordingProvider, *, builder) -> AgentSpec:
    return AgentSpec(
        id=AgentId("phronesis.agents.x"),
        name="x",
        model=provider,
        system_prompt="be brief",
        max_iterations=3,
        context_builder=builder,
    )


class TestBuilderInvocation:
    @pytest.mark.asyncio
    async def test_builder_is_invoked_each_iteration(self) -> None:
        provider = _RecordingProvider([LLMResponse(text="done", finish_reason="stop")])
        builder = _RecordingBuilder()
        spec = _spec(provider, builder=builder)

        await run_loop(spec, RunRequest(input="hi"))

        assert len(builder.calls) == 1

    @pytest.mark.asyncio
    async def test_builder_receives_seeded_system_in_history(self) -> None:
        provider = _RecordingProvider([LLMResponse(text="done", finish_reason="stop")])
        builder = _RecordingBuilder()
        spec = _spec(provider, builder=builder)

        await run_loop(spec, RunRequest(input="hi"))

        call = builder.calls[0]
        # The loop seeds the system prompt into history.
        assert call.history
        assert isinstance(call.history[0], SystemMessage)

    @pytest.mark.asyncio
    async def test_builder_receives_provider_reference(self) -> None:
        provider = _RecordingProvider([LLMResponse(text="done", finish_reason="stop")])
        builder = _RecordingBuilder()
        spec = _spec(provider, builder=builder)

        await run_loop(spec, RunRequest(input="hi"))

        assert builder.calls[0].provider is provider

    @pytest.mark.asyncio
    async def test_builder_receives_user_input_as_new_input(self) -> None:
        provider = _RecordingProvider([LLMResponse(text="done", finish_reason="stop")])
        builder = _RecordingBuilder()
        spec = _spec(provider, builder=builder)

        await run_loop(spec, RunRequest(input="hello there"))

        first_call = builder.calls[0]
        assert isinstance(first_call.new_input, UserMessage)
        block = first_call.new_input.content[0]
        assert isinstance(block, TextBlock)
        assert block.text == "hello there"


class TestCustomBuilderOutput:
    @pytest.mark.asyncio
    async def test_custom_builder_messages_reach_provider(self) -> None:
        provider = _RecordingProvider([LLMResponse(text="done", finish_reason="stop")])
        builder = _CustomPrefixBuilder()
        spec = _spec(provider, builder=builder)

        await run_loop(spec, RunRequest(input="hi"))

        # Inspect provider-facing wire messages for the marker text.
        request = provider.requests[0]
        assistant_texts = [
            m.content
            for m in request.messages
            if isinstance(m.content, str) and "<<builder-marker>>" in m.content
        ]
        assert assistant_texts
