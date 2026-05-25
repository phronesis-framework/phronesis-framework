"""Tests for ``phronesis.providers.anthropic.messages``."""

from __future__ import annotations

from phronesis.providers.anthropic.messages import (
    from_anthropic_content,
    to_anthropic_messages,
)
from phronesis.providers.types import Message, Role, ToolCall


class TestToAnthropicMessages:
    def test_user_only(self) -> None:
        msgs, system = to_anthropic_messages([Message(role=Role.USER, content="hi")])

        assert system is None
        assert msgs == [{"role": "user", "content": [{"type": "text", "text": "hi"}]}]

    def test_system_extracted_to_top_level(self) -> None:
        msgs, system = to_anthropic_messages(
            [
                Message(role=Role.SYSTEM, content="be helpful"),
                Message(role=Role.USER, content="hi"),
            ],
        )

        assert system == "be helpful"
        assert msgs == [{"role": "user", "content": [{"type": "text", "text": "hi"}]}]

    def test_multiple_system_messages_joined(self) -> None:
        _, system = to_anthropic_messages(
            [
                Message(role=Role.SYSTEM, content="be helpful"),
                Message(role=Role.SYSTEM, content="be concise"),
                Message(role=Role.USER, content="hi"),
            ],
        )

        assert system == "be helpful\n\nbe concise"

    def test_empty_system_message_skipped(self) -> None:
        _, system = to_anthropic_messages(
            [
                Message(role=Role.SYSTEM, content=""),
                Message(role=Role.USER, content="hi"),
            ],
        )

        assert system is None

    def test_assistant_with_text(self) -> None:
        msgs, _ = to_anthropic_messages(
            [Message(role=Role.ASSISTANT, content="hello")],
        )

        assert msgs == [{"role": "assistant", "content": [{"type": "text", "text": "hello"}]}]

    def test_assistant_with_tool_calls(self) -> None:
        call = ToolCall(call_id="c1", tool_name="search", arguments={"q": "x"})
        msgs, _ = to_anthropic_messages(
            [Message(role=Role.ASSISTANT, content="thinking", tool_calls=(call,))],
        )

        assert msgs == [
            {
                "role": "assistant",
                "content": [
                    {"type": "text", "text": "thinking"},
                    {
                        "type": "tool_use",
                        "id": "c1",
                        "name": "search",
                        "input": {"q": "x"},
                    },
                ],
            }
        ]

    def test_assistant_tool_calls_only_omits_text_block(self) -> None:
        call = ToolCall(call_id="c1", tool_name="search", arguments={})
        msgs, _ = to_anthropic_messages(
            [Message(role=Role.ASSISTANT, tool_calls=(call,))],
        )

        assert msgs[0]["content"] == [
            {"type": "tool_use", "id": "c1", "name": "search", "input": {}}
        ]

    def test_tool_message_becomes_user_tool_result(self) -> None:
        msgs, _ = to_anthropic_messages(
            [Message(role=Role.TOOL, tool_call_id="c1", tool_output={"ok": True})],
        )

        assert msgs == [
            {
                "role": "user",
                "content": [
                    {
                        "type": "tool_result",
                        "tool_use_id": "c1",
                        "content": '{"ok": true}',
                    }
                ],
            }
        ]

    def test_tool_message_with_string_output_passes_through(self) -> None:
        msgs, _ = to_anthropic_messages(
            [Message(role=Role.TOOL, tool_call_id="c1", tool_output="raw text")],
        )

        assert msgs[0]["content"][0]["content"] == "raw text"


class TestFromAnthropicContent:
    def test_empty_blocks(self) -> None:
        text, calls = from_anthropic_content([])

        assert text == ""
        assert calls == ()

    def test_text_blocks_concatenated(self) -> None:
        text, calls = from_anthropic_content(
            [
                {"type": "text", "text": "hello "},
                {"type": "text", "text": "world"},
            ]
        )

        assert text == "hello world"
        assert calls == ()

    def test_tool_use_block_parsed(self) -> None:
        text, calls = from_anthropic_content(
            [
                {"type": "text", "text": "ok"},
                {
                    "type": "tool_use",
                    "id": "c1",
                    "name": "search",
                    "input": {"q": "x"},
                },
            ]
        )

        assert text == "ok"
        assert calls == (ToolCall(call_id="c1", tool_name="search", arguments={"q": "x"}),)

    def test_unknown_block_ignored(self) -> None:
        text, calls = from_anthropic_content(
            [{"type": "image", "source": "..."}, {"type": "text", "text": "hi"}],
        )

        assert text == "hi"
        assert calls == ()

    def test_tool_use_with_non_dict_input_defaults_empty(self) -> None:
        _, calls = from_anthropic_content(
            [{"type": "tool_use", "id": "c1", "name": "t", "input": "broken"}],
        )

        assert calls == (ToolCall(call_id="c1", tool_name="t", arguments={}),)
