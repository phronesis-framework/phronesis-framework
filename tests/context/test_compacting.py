"""Tests for :class:`phronesis.context.CompactingContextBuilder`."""

from __future__ import annotations

import asyncio

import pytest

from phronesis.context.compacting import CompactingContextBuilder
from phronesis.context.errors import CompactionError
from phronesis.context.input import BuildInput
from phronesis.core.messages import (
    AssistantMessage,
    CompactionSummaryBlock,
    SystemMessage,
    TextBlock,
    ToolMessage,
    ToolResultBlock,
    ToolUseBlock,
    UserMessage,
)
from tests.context.conftest import ExplodingProvider, FakeProvider


def _input(provider: FakeProvider, *, system_prompt: str = "sys", history=(), new_input=None):
    return BuildInput(
        system_prompt=system_prompt,
        history=tuple(history),
        new_input=new_input,
        provider=provider,
    )


def _user(text: str) -> UserMessage:
    return UserMessage(content=(TextBlock(text=text),))


def _assistant(text: str) -> AssistantMessage:
    return AssistantMessage(content=(TextBlock(text=text),))


class TestBelowThreshold:
    @pytest.mark.asyncio
    async def test_below_threshold_does_not_call_provider(self) -> None:
        provider = FakeProvider(context_window=1_000, token_estimate=100)
        builder = CompactingContextBuilder(threshold_ratio=0.8)
        history = tuple(_user(f"msg-{i}") for i in range(4))

        result = await builder.build(_input(provider, history=history))

        assert provider.requests == []
        assert all(not isinstance(m.content[0], CompactionSummaryBlock) for m in result)

    @pytest.mark.asyncio
    async def test_zero_context_window_skips_compaction(self) -> None:
        provider = FakeProvider(context_window=0, token_estimate=999_999)
        builder = CompactingContextBuilder()

        result = await builder.build(_input(provider, history=(_user("hi"),)))

        assert provider.requests == []
        assert len(result) >= 1

    @pytest.mark.asyncio
    async def test_empty_history_does_not_compact(self) -> None:
        provider = FakeProvider(context_window=1_000, token_estimate=100_000)
        builder = CompactingContextBuilder()

        result = await builder.build(_input(provider, history=()))

        assert provider.requests == []
        assert result == [SystemMessage(content=(TextBlock(text="sys"),))]


class TestCompaction:
    @pytest.mark.asyncio
    async def test_above_threshold_calls_compactor(self) -> None:
        provider = FakeProvider(
            response_text="summary text", context_window=1_000, token_estimate=900
        )
        builder = CompactingContextBuilder(preserve_recent=2)
        history = tuple(_user(f"old-{i}") for i in range(10))

        result = await builder.build(_input(provider, history=history))

        assert len(provider.requests) == 1
        summary_present = any(
            isinstance(m, AssistantMessage)
            and any(isinstance(b, CompactionSummaryBlock) for b in m.content)
            for m in result
        )
        assert summary_present

    @pytest.mark.asyncio
    async def test_preserves_recent_messages(self) -> None:
        provider = FakeProvider(context_window=1_000, token_estimate=900)
        builder = CompactingContextBuilder(preserve_recent=3)
        history = tuple(_user(f"m-{i}") for i in range(10))

        result = await builder.build(_input(provider, history=history))

        last_three_texts = [history[-3], history[-2], history[-1]]
        assert result[-3:] == last_three_texts

    @pytest.mark.asyncio
    async def test_summary_block_records_original_count(self) -> None:
        provider = FakeProvider(context_window=1_000, token_estimate=900)
        builder = CompactingContextBuilder(preserve_recent=2)
        history = tuple(_user(f"m-{i}") for i in range(8))

        result = await builder.build(_input(provider, history=history))

        summary = next(
            m
            for m in result
            if isinstance(m, AssistantMessage)
            and any(isinstance(b, CompactionSummaryBlock) for b in m.content)
        )
        block = next(b for b in summary.content if isinstance(b, CompactionSummaryBlock))
        # 8 messages total, preserve_recent=2 → 6 compactable.
        assert block.original_message_count == 6


class TestExistingSummary:
    @pytest.mark.asyncio
    async def test_prior_summary_is_preserved(self) -> None:
        provider = FakeProvider(
            response_text="new summary", context_window=1_000, token_estimate=900
        )
        builder = CompactingContextBuilder(preserve_recent=2)
        prior_summary = AssistantMessage(
            content=(CompactionSummaryBlock(text="old summary", original_message_count=5),)
        )
        history = (prior_summary, *(_user(f"m-{i}") for i in range(8)))

        result = await builder.build(_input(provider, history=history))

        summaries = [
            m
            for m in result
            if isinstance(m, AssistantMessage)
            and any(isinstance(b, CompactionSummaryBlock) for b in m.content)
        ]
        assert len(summaries) == 2
        # The prior summary is first.
        first_block = next(b for b in summaries[0].content if isinstance(b, CompactionSummaryBlock))
        assert first_block.text == "old summary"


class TestToolPairPreservation:
    @pytest.mark.asyncio
    async def test_split_does_not_break_tool_pair(self) -> None:
        provider = FakeProvider(context_window=1_000, token_estimate=900)
        builder = CompactingContextBuilder(preserve_recent=2)

        tool_use_msg = AssistantMessage(
            content=(ToolUseBlock(tool_call_id="t1", tool_name="echo", args=(("v", "x"),)),)
        )
        tool_result_msg = ToolMessage(content=(ToolResultBlock(tool_call_id="t1", output="ok"),))

        # Place the tool_use right at the boundary so the naive split
        # would land between tool_use and tool_result.
        history = (
            _user("old-1"),
            _user("old-2"),
            tool_use_msg,
            tool_result_msg,
            _user("recent"),
        )

        result = await builder.build(_input(provider, history=history))

        # The tool_result must not appear in 'preserved' without its tool_use.
        tool_result_idx = next((i for i, m in enumerate(result) if m is tool_result_msg), None)
        if tool_result_idx is not None:
            assert tool_use_msg in result[:tool_result_idx]


class TestLeadingSystemPreservation:
    @pytest.mark.asyncio
    async def test_leading_system_messages_kept_verbatim(self) -> None:
        provider = FakeProvider(context_window=1_000, token_estimate=900)
        builder = CompactingContextBuilder(preserve_recent=2)
        sys_msg = SystemMessage(content=(TextBlock(text="seed sys"),))
        history = (sys_msg, *(_user(f"m-{i}") for i in range(8)))

        result = await builder.build(_input(provider, history=history))

        assert result[0] is sys_msg


class TestCompactionErrors:
    @pytest.mark.asyncio
    async def test_compactor_failure_raises_compaction_error(self) -> None:
        provider = ExplodingProvider(context_window=1_000, token_estimate=900)
        builder = CompactingContextBuilder(preserve_recent=2)
        history = tuple(_user(f"m-{i}") for i in range(6))

        with pytest.raises(CompactionError) as info:
            await builder.build(_input(provider, history=history))

        assert info.value.details["provider"] == "ExplodingProvider"
        assert info.value.details["history_size"] == 6
        assert isinstance(info.value.__cause__, RuntimeError)


class TestCompactorOverride:
    @pytest.mark.asyncio
    async def test_compactor_provider_override_is_used(self) -> None:
        run_provider = FakeProvider(context_window=1_000, token_estimate=900)
        compactor = FakeProvider(response_text="OVERRIDE")
        builder = CompactingContextBuilder(preserve_recent=2, compactor_provider=compactor)
        history = tuple(_user(f"m-{i}") for i in range(6))

        result = await builder.build(_input(run_provider, history=history))

        assert run_provider.requests == []
        assert len(compactor.requests) == 1
        summary = next(
            m
            for m in result
            if isinstance(m, AssistantMessage)
            and any(isinstance(b, CompactionSummaryBlock) for b in m.content)
        )
        block = next(b for b in summary.content if isinstance(b, CompactionSummaryBlock))
        assert block.text == "OVERRIDE"


class TestStatelessness:
    @pytest.mark.asyncio
    async def test_concurrent_builds_do_not_share_state(self) -> None:
        provider = FakeProvider(context_window=1_000, token_estimate=900)
        builder = CompactingContextBuilder(preserve_recent=2)

        history_a = tuple(_user(f"a-{i}") for i in range(6))
        history_b = tuple(_assistant(f"b-{i}") for i in range(6))

        results = await asyncio.gather(
            builder.build(_input(provider, history=history_a)),
            builder.build(_input(provider, history=history_b)),
        )

        # Both builds produced a summary message each.
        for res in results:
            assert any(
                isinstance(m, AssistantMessage)
                and any(isinstance(b, CompactionSummaryBlock) for b in m.content)
                for m in res
            )
