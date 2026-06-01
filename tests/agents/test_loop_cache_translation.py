"""Tests that ``TextBlock.cache`` flows through the loop translator."""

from __future__ import annotations

from phronesis.agents.loop import _translate_history
from phronesis.core.messages import (
    AssistantMessage,
    SystemMessage,
    TextBlock,
    ToolUseBlock,
    UserMessage,
)


class TestCachePropagation:
    def test_system_text_cache_flag_propagates(self) -> None:
        history = (SystemMessage(content=(TextBlock(text="static prompt", cache=True),)),)

        translated = _translate_history(history)

        assert translated[0].cache is True

    def test_user_text_cache_flag_propagates(self) -> None:
        history = (UserMessage(content=(TextBlock(text="cached context", cache=True),)),)

        translated = _translate_history(history)

        assert translated[0].cache is True

    def test_assistant_text_cache_flag_propagates(self) -> None:
        history = (
            AssistantMessage(
                content=(
                    TextBlock(text="picking a tool", cache=True),
                    ToolUseBlock(tool_call_id="t1", tool_name="x", args={}),
                ),
            ),
        )

        translated = _translate_history(history)

        assert translated[0].cache is True

    def test_default_cache_flag_is_false(self) -> None:
        history = (
            SystemMessage(content=(TextBlock(text="default"),)),
            UserMessage(content=(TextBlock(text="default"),)),
        )

        translated = _translate_history(history)

        assert all(m.cache is False for m in translated)

    def test_cache_flag_independent_per_message(self) -> None:
        history = (
            SystemMessage(content=(TextBlock(text="cached", cache=True),)),
            UserMessage(content=(TextBlock(text="uncached"),)),
        )

        translated = _translate_history(history)

        assert translated[0].cache is True
        assert translated[1].cache is False
