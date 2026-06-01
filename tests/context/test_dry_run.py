"""Tests for :func:`dry_run`."""

from __future__ import annotations

from collections.abc import Sequence

import pytest

from phronesis.context.default import DefaultContextBuilder
from phronesis.context.dry_run import DryRunReport, dry_run
from phronesis.core.messages import Message, TextBlock, UserMessage
from phronesis.providers.protocol import ProviderFeature
from phronesis.providers.types import LLMRequest, LLMResponse


class _StubProvider:
    def __init__(self, window: int = 1000, count: int = 7) -> None:
        self._window = window
        self._count = count

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
        return self._window

    def count_tokens(self, messages: Sequence[Message]) -> int:
        return self._count


class TestDryRun:
    @pytest.mark.asyncio
    async def test_returns_messages_and_counts(self) -> None:
        report = await dry_run(
            DefaultContextBuilder(),
            provider=_StubProvider(window=1000, count=7),  # type: ignore[arg-type]
            system_prompt="sys",
            new_input=UserMessage(content=(TextBlock(text="hi"),)),
        )

        assert isinstance(report, DryRunReport)
        assert report.message_count == len(report.messages)
        assert report.token_estimate == 7
        assert report.window_size == 1000
        assert report.within_window is True

    @pytest.mark.asyncio
    async def test_within_window_false_when_over(self) -> None:
        report = await dry_run(
            DefaultContextBuilder(),
            provider=_StubProvider(window=5, count=10),  # type: ignore[arg-type]
            system_prompt="sys",
        )

        assert report.within_window is False
