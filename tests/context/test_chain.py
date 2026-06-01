"""Tests for :class:`ChainedContextBuilder` and :func:`chain`."""

from __future__ import annotations

from collections.abc import Sequence

import pytest

from phronesis.context.chain import ChainedContextBuilder, chain
from phronesis.context.default import DefaultContextBuilder
from phronesis.context.input import BuildInput
from phronesis.core.messages import (
    AssistantMessage,
    Message,
    SystemMessage,
    TextBlock,
    UserMessage,
)
from phronesis.providers.protocol import ProviderFeature
from phronesis.providers.types import LLMRequest, LLMResponse


class _StubProvider:
    async def complete(self, request: LLMRequest) -> LLMResponse:
        return LLMResponse(text="x", finish_reason="stop")

    def stream(self, request: LLMRequest):  # type: ignore[no-untyped-def]
        async def _empty():  # type: ignore[no-untyped-def]
            return
            yield  # pragma: no cover

        return _empty()

    def supports(self, feature: ProviderFeature) -> bool:
        return False

    def context_window_size(self) -> int:
        return 200_000

    def count_tokens(self, messages: Sequence[Message]) -> int:
        return 0


class _MarkerBuilder:
    """Appends a marker AssistantMessage and forwards the rest."""

    def __init__(self, marker: str) -> None:
        self.marker = marker
        self.calls: list[BuildInput] = []

    async def build(self, input: BuildInput) -> list[Message]:
        self.calls.append(input)
        msgs: list[Message] = []

        if input.system_prompt:
            msgs.append(SystemMessage(content=(TextBlock(text=input.system_prompt),)))

        msgs.extend(input.history)
        msgs.append(AssistantMessage(content=(TextBlock(text=self.marker),)))

        if input.new_input is not None:
            msgs.append(input.new_input)

        return msgs


def _input() -> BuildInput:
    return BuildInput(
        system_prompt="sys",
        history=(UserMessage(content=(TextBlock(text="prior"),)),),
        new_input=UserMessage(content=(TextBlock(text="now"),)),
        provider=_StubProvider(),  # type: ignore[arg-type]
    )


class TestChain:
    @pytest.mark.asyncio
    async def test_empty_chain_rejected(self) -> None:
        with pytest.raises(ValueError):
            ChainedContextBuilder(())

    @pytest.mark.asyncio
    async def test_single_builder_passes_input_through(self) -> None:
        marker = _MarkerBuilder("A")
        chained = chain(marker)

        messages = await chained.build(_input())

        assert any(
            isinstance(m, AssistantMessage)
            and any(getattr(b, "text", "") == "A" for b in m.content)
            for m in messages
        )

    @pytest.mark.asyncio
    async def test_second_builder_receives_no_new_input(self) -> None:
        a = _MarkerBuilder("A")
        b = _MarkerBuilder("B")
        chained = chain(a, b)

        await chained.build(_input())

        assert a.calls[0].new_input is not None
        assert b.calls[0].new_input is None

    @pytest.mark.asyncio
    async def test_second_builder_does_not_see_duplicate_system(self) -> None:
        a = _MarkerBuilder("A")
        b = _MarkerBuilder("B")
        chained = chain(a, b)

        await chained.build(_input())

        # b's input.history must not contain a SystemMessage; b will add
        # its own from input.system_prompt.
        history = b.calls[0].history
        assert not any(isinstance(m, SystemMessage) for m in history)

    @pytest.mark.asyncio
    async def test_chain_with_default_builder(self) -> None:
        chained = chain(DefaultContextBuilder(), _MarkerBuilder("Z"))

        messages = await chained.build(_input())

        assert any(
            isinstance(m, AssistantMessage)
            and any(getattr(b, "text", "") == "Z" for b in m.content)
            for m in messages
        )
