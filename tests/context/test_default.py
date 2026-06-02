"""Tests for :class:`phronesis.context.DefaultContextBuilder`."""

from __future__ import annotations

import pytest

from phronesis.context.default import DefaultContextBuilder
from phronesis.context.input import BuildInput
from phronesis.core.messages import (
    AssistantMessage,
    SystemMessage,
    TextBlock,
    UserMessage,
)
from tests.context.conftest import FakeProvider


def _input(
    *,
    system_prompt: str = "",
    history: tuple = (),
    new_input=None,
) -> BuildInput:
    return BuildInput(
        system_prompt=system_prompt,
        history=history,
        new_input=new_input,
        provider=FakeProvider(),
    )


class TestEmptyHistory:
    @pytest.mark.asyncio
    async def test_empty_history_without_prompt_returns_empty(self) -> None:
        builder = DefaultContextBuilder()

        result = await builder.build(_input())

        assert result == []

    @pytest.mark.asyncio
    async def test_empty_history_with_prompt_emits_system(self) -> None:
        builder = DefaultContextBuilder()

        result = await builder.build(_input(system_prompt="be brief"))

        assert len(result) == 1
        assert isinstance(result[0], SystemMessage)


class TestHistoryWithSystemPrompt:
    @pytest.mark.asyncio
    async def test_history_starts_with_system_skips_extra_prompt(self) -> None:
        builder = DefaultContextBuilder()
        history = (
            SystemMessage(content=(TextBlock(text="sys"),)),
            UserMessage(content=(TextBlock(text="hi"),)),
        )

        result = await builder.build(_input(system_prompt="other", history=history))

        # No duplicate SystemMessage appended.
        assert len(result) == 2
        assert isinstance(result[0], SystemMessage)
        assert isinstance(result[1], UserMessage)

    @pytest.mark.asyncio
    async def test_history_without_leading_system_gets_prompt_prepended(self) -> None:
        builder = DefaultContextBuilder()
        history = (UserMessage(content=(TextBlock(text="hi"),)),)

        result = await builder.build(_input(system_prompt="sys", history=history))

        assert len(result) == 2
        assert isinstance(result[0], SystemMessage)
        assert isinstance(result[1], UserMessage)


class TestNewInputAppending:
    @pytest.mark.asyncio
    async def test_new_input_is_appended_last(self) -> None:
        builder = DefaultContextBuilder()
        prior = UserMessage(content=(TextBlock(text="first"),))
        new = UserMessage(content=(TextBlock(text="second"),))

        result = await builder.build(_input(history=(prior,), new_input=new))

        assert result[-1] is new

    @pytest.mark.asyncio
    async def test_none_new_input_is_skipped(self) -> None:
        builder = DefaultContextBuilder()
        prior = UserMessage(content=(TextBlock(text="only"),))

        result = await builder.build(_input(history=(prior,), new_input=None))

        assert result == [prior]


class TestStatelessness:
    @pytest.mark.asyncio
    async def test_multiple_builds_do_not_share_state(self) -> None:
        builder = DefaultContextBuilder()

        result_a = await builder.build(
            _input(history=(UserMessage(content=(TextBlock(text="a"),)),))
        )
        result_b = await builder.build(
            _input(history=(AssistantMessage(content=(TextBlock(text="b"),)),))
        )

        assert len(result_a) == 1
        assert len(result_b) == 1
        assert type(result_a[0]).__name__ == "UserMessage"
        assert type(result_b[0]).__name__ == "AssistantMessage"
