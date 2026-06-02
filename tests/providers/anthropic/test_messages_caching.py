"""Tests for prompt-caching markers in the Anthropic translator."""

from __future__ import annotations

from phronesis.providers.anthropic.messages import to_anthropic_messages
from phronesis.providers.types import Message, Role, ToolCall


class TestUserCaching:
    def test_cache_flag_emits_cache_control_on_user_block(self) -> None:
        msgs, _ = to_anthropic_messages(
            [Message(role=Role.USER, content="long static context", cache=True)],
        )

        assert msgs == [
            {
                "role": "user",
                "content": [
                    {
                        "type": "text",
                        "text": "long static context",
                        "cache_control": {"type": "ephemeral"},
                    },
                ],
            },
        ]

    def test_no_cache_flag_omits_cache_control(self) -> None:
        msgs, _ = to_anthropic_messages(
            [Message(role=Role.USER, content="hi")],
        )

        assert msgs == [{"role": "user", "content": [{"type": "text", "text": "hi"}]}]
        assert "cache_control" not in msgs[0]["content"][0]


class TestSystemCaching:
    def test_no_cache_uses_plain_string(self) -> None:
        _, system = to_anthropic_messages(
            [Message(role=Role.SYSTEM, content="be helpful")],
        )

        assert system == "be helpful"

    def test_cache_flag_promotes_system_to_block_list(self) -> None:
        _, system = to_anthropic_messages(
            [Message(role=Role.SYSTEM, content="be helpful", cache=True)],
        )

        assert system == [
            {
                "type": "text",
                "text": "be helpful",
                "cache_control": {"type": "ephemeral"},
            },
        ]

    def test_mixed_system_marks_only_cached_chunks(self) -> None:
        _, system = to_anthropic_messages(
            [
                Message(role=Role.SYSTEM, content="be helpful", cache=True),
                Message(role=Role.SYSTEM, content="be concise"),
            ],
        )

        assert system == [
            {
                "type": "text",
                "text": "be helpful",
                "cache_control": {"type": "ephemeral"},
            },
            {"type": "text", "text": "be concise"},
        ]


class TestAssistantCaching:
    def test_cache_marker_on_assistant_text(self) -> None:
        msgs, _ = to_anthropic_messages(
            [Message(role=Role.ASSISTANT, content="here is the answer", cache=True)],
        )

        assert msgs == [
            {
                "role": "assistant",
                "content": [
                    {
                        "type": "text",
                        "text": "here is the answer",
                        "cache_control": {"type": "ephemeral"},
                    },
                ],
            },
        ]

    def test_cache_marker_lands_on_last_block_when_tools_present(self) -> None:
        msgs, _ = to_anthropic_messages(
            [
                Message(
                    role=Role.ASSISTANT,
                    content="picking a tool",
                    tool_calls=(ToolCall(call_id="t1", tool_name="search", arguments={"q": "hi"}),),
                    cache=True,
                ),
            ],
        )

        blocks = msgs[0]["content"]
        assert len(blocks) == 2
        # text block remains untouched
        assert blocks[0] == {"type": "text", "text": "picking a tool"}
        # cache_control rides on the last block (the tool_use)
        assert blocks[1]["type"] == "tool_use"
        assert blocks[1]["cache_control"] == {"type": "ephemeral"}


class TestToolCaching:
    def test_cache_marker_on_tool_result(self) -> None:
        msgs, _ = to_anthropic_messages(
            [
                Message(
                    role=Role.TOOL,
                    tool_call_id="t1",
                    tool_output="42",
                    cache=True,
                ),
            ],
        )

        assert msgs == [
            {
                "role": "user",
                "content": [
                    {
                        "type": "tool_result",
                        "tool_use_id": "t1",
                        "content": "42",
                        "cache_control": {"type": "ephemeral"},
                    },
                ],
            },
        ]
