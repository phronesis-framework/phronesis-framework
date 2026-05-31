"""Tests for domain message and content block types."""

from __future__ import annotations

from types import MappingProxyType

import pytest

from phronesis.core.messages import (
    AssistantMessage,
    CompactionSummaryBlock,
    ContentBlock,
    Message,
    SystemMessage,
    TextBlock,
    ToolMessage,
    ToolResultBlock,
    ToolUseBlock,
    UserMessage,
)


class TestTextBlock:
    def test_holds_text(self) -> None:
        block = TextBlock(text="hello")

        assert block.text == "hello"

    def test_is_frozen(self) -> None:
        block = TextBlock(text="hi")

        with pytest.raises(AttributeError):
            block.text = "other"  # type: ignore[misc]

    def test_equality_is_value_based(self) -> None:
        assert TextBlock(text="a") == TextBlock(text="a")
        assert TextBlock(text="a") != TextBlock(text="b")


class TestToolUseBlock:
    def test_default_args_is_empty(self) -> None:
        block = ToolUseBlock(tool_call_id="c1", tool_name="search")

        assert dict(block.args) == {}

    def test_stored_args_are_immutable(self) -> None:
        payload = {"q": "phronesis"}

        block = ToolUseBlock(tool_call_id="c1", tool_name="search", args=payload)
        payload["q"] = "mutated"

        assert dict(block.args) == {"q": "phronesis"}
        assert isinstance(block.args, MappingProxyType)

    def test_is_frozen(self) -> None:
        block = ToolUseBlock(tool_call_id="c1", tool_name="search")

        with pytest.raises(AttributeError):
            block.tool_name = "other"  # type: ignore[misc]


class TestToolResultBlock:
    def test_default_is_not_error(self) -> None:
        block = ToolResultBlock(tool_call_id="c1", output={"ok": True})

        assert block.is_error is False
        assert block.output == {"ok": True}

    def test_error_flag_round_trips(self) -> None:
        block = ToolResultBlock(
            tool_call_id="c1",
            output={"error": "tool_timeout"},
            is_error=True,
        )

        assert block.is_error is True

    def test_is_frozen(self) -> None:
        block = ToolResultBlock(tool_call_id="c1", output=None)

        with pytest.raises(AttributeError):
            block.is_error = True  # type: ignore[misc]


class TestCompactionSummaryBlock:
    def test_holds_text_and_count(self) -> None:
        block = CompactionSummaryBlock(text="summary", original_message_count=12)

        assert block.text == "summary"
        assert block.original_message_count == 12

    def test_is_frozen(self) -> None:
        block = CompactionSummaryBlock(text="s", original_message_count=1)

        with pytest.raises(AttributeError):
            block.text = "other"  # type: ignore[misc]

    def test_equality_is_value_based(self) -> None:
        a = CompactionSummaryBlock(text="x", original_message_count=3)
        b = CompactionSummaryBlock(text="x", original_message_count=3)

        assert a == b
        assert a != CompactionSummaryBlock(text="x", original_message_count=4)


class TestContentBlockUnion:
    @pytest.mark.parametrize(
        "block",
        [
            TextBlock(text="hi"),
            ToolUseBlock(tool_call_id="c1", tool_name="search"),
            ToolResultBlock(tool_call_id="c1", output=None),
            CompactionSummaryBlock(text="s", original_message_count=2),
        ],
    )
    def test_every_block_is_a_content_block(self, block: ContentBlock) -> None:
        assert isinstance(
            block,
            TextBlock | ToolUseBlock | ToolResultBlock | CompactionSummaryBlock,
        )


class TestMessageTypes:
    def test_system_message_holds_content(self) -> None:
        msg = SystemMessage(content=(TextBlock(text="be helpful"),))

        assert msg.content == (TextBlock(text="be helpful"),)

    def test_user_message_holds_content(self) -> None:
        msg = UserMessage(content=(TextBlock(text="hi"),))

        assert msg.content == (TextBlock(text="hi"),)

    def test_assistant_message_can_mix_text_and_tool_use(self) -> None:
        msg = AssistantMessage(
            content=(
                TextBlock(text="let me check"),
                ToolUseBlock(tool_call_id="c1", tool_name="search"),
            ),
        )

        assert len(msg.content) == 2
        assert isinstance(msg.content[1], ToolUseBlock)

    def test_tool_message_carries_result_blocks(self) -> None:
        msg = ToolMessage(
            content=(ToolResultBlock(tool_call_id="c1", output={"hits": 0}),),
        )

        assert isinstance(msg.content[0], ToolResultBlock)


class TestMessageUnion:
    @pytest.mark.parametrize(
        "msg",
        [
            SystemMessage(content=()),
            UserMessage(content=()),
            AssistantMessage(content=()),
            ToolMessage(content=()),
        ],
    )
    def test_every_role_is_a_message(self, msg: Message) -> None:
        assert isinstance(
            msg,
            SystemMessage | UserMessage | AssistantMessage | ToolMessage,
        )

    def test_messages_are_frozen(self) -> None:
        msg = UserMessage(content=())

        with pytest.raises(AttributeError):
            msg.content = (TextBlock(text="x"),)  # type: ignore[misc]

    def test_messages_equality_is_value_based(self) -> None:
        a = UserMessage(content=(TextBlock(text="hi"),))
        b = UserMessage(content=(TextBlock(text="hi"),))

        assert a == b
