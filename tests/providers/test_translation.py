"""Tests for ``phronesis.providers.translation``."""

from __future__ import annotations

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
from phronesis.providers.translation import translate_history
from phronesis.providers.types import Role as ProviderRole


class TestTranslateHistory:
    def test_empty_history(self) -> None:
        assert translate_history(()) == ()

    def test_system_user_assistant_round_trip(self) -> None:
        history = (
            SystemMessage(content=(TextBlock(text="sys"),)),
            UserMessage(content=(TextBlock(text="hi"),)),
            AssistantMessage(content=(TextBlock(text="hello"),)),
        )

        translated = translate_history(history)

        assert [m.role for m in translated] == [
            ProviderRole.SYSTEM,
            ProviderRole.USER,
            ProviderRole.ASSISTANT,
        ]
        assert [m.content for m in translated] == ["sys", "hi", "hello"]

    def test_assistant_tool_use_becomes_tool_call(self) -> None:
        history = (
            AssistantMessage(
                content=(
                    TextBlock(text="thinking"),
                    ToolUseBlock(tool_call_id="t1", tool_name="search", args={"q": "x"}),
                ),
            ),
        )

        translated = translate_history(history)

        assert len(translated) == 1
        assert translated[0].tool_calls[0].call_id == "t1"
        assert translated[0].tool_calls[0].tool_name == "search"
        assert translated[0].tool_calls[0].arguments == {"q": "x"}

    def test_tool_message_explodes_per_result_block(self) -> None:
        history = (
            ToolMessage(
                content=(
                    ToolResultBlock(tool_call_id="t1", output="a"),
                    ToolResultBlock(tool_call_id="t2", output="b"),
                ),
            ),
        )

        translated = translate_history(history)

        assert len(translated) == 2
        assert translated[0].tool_call_id == "t1"
        assert translated[1].tool_call_id == "t2"

    def test_compaction_summary_concatenated_as_text(self) -> None:
        history = (
            SystemMessage(
                content=(CompactionSummaryBlock(text="summary", original_message_count=4),),
            ),
        )

        translated = translate_history(history)

        assert translated[0].content == "summary"

    def test_cache_flag_propagates(self) -> None:
        history = (UserMessage(content=(TextBlock(text="cached", cache=True),)),)

        translated = translate_history(history)

        assert translated[0].cache is True

    def test_cache_flag_default_false(self) -> None:
        history = (UserMessage(content=(TextBlock(text="plain"),)),)

        translated = translate_history(history)

        assert translated[0].cache is False
