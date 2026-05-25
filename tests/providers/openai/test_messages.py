"""Tests for ``phronesis.providers.openai.messages``."""

from __future__ import annotations

import json

from phronesis.providers.openai.messages import from_openai_message, to_openai_messages
from phronesis.providers.types import Message, Role, ToolCall


class TestToOpenaiMessages:
    def test_empty_input(self) -> None:
        assert to_openai_messages([]) == []

    def test_system_user_assistant_round_trip(self) -> None:
        messages = [
            Message(role=Role.SYSTEM, content="be helpful"),
            Message(role=Role.USER, content="hi"),
            Message(role=Role.ASSISTANT, content="hello"),
        ]

        result = to_openai_messages(messages)

        assert result == [
            {"role": "system", "content": "be helpful"},
            {"role": "user", "content": "hi"},
            {"role": "assistant", "content": "hello"},
        ]

    def test_assistant_with_tool_calls(self) -> None:
        message = Message(
            role=Role.ASSISTANT,
            content="thinking",
            tool_calls=(ToolCall(call_id="call_1", tool_name="search", arguments={"q": "hi"}),),
        )

        result = to_openai_messages([message])

        assert result[0]["role"] == "assistant"
        assert result[0]["content"] == "thinking"
        assert result[0]["tool_calls"] == [
            {
                "id": "call_1",
                "type": "function",
                "function": {"name": "search", "arguments": json.dumps({"q": "hi"})},
            }
        ]

    def test_assistant_with_only_tool_calls_sends_null_content(self) -> None:
        message = Message(
            role=Role.ASSISTANT,
            tool_calls=(ToolCall(call_id="c1", tool_name="t", arguments={}),),
        )

        result = to_openai_messages([message])

        assert result[0]["content"] is None

    def test_tool_message_uses_tool_call_id_and_output(self) -> None:
        message = Message(
            role=Role.TOOL,
            tool_call_id="call_1",
            tool_output={"result": 42},
        )

        result = to_openai_messages([message])

        assert result[0] == {
            "role": "tool",
            "tool_call_id": "call_1",
            "content": json.dumps({"result": 42}),
        }

    def test_tool_message_string_output_passes_through(self) -> None:
        message = Message(role=Role.TOOL, tool_call_id="c1", tool_output="ok")

        assert to_openai_messages([message])[0]["content"] == "ok"

    def test_tool_message_falls_back_to_content(self) -> None:
        message = Message(role=Role.TOOL, tool_call_id="c1", content="fallback")

        assert to_openai_messages([message])[0]["content"] == "fallback"


class TestFromOpenaiMessage:
    def test_text_only(self) -> None:
        text, calls = from_openai_message({"role": "assistant", "content": "hi"})

        assert text == "hi"
        assert calls == ()

    def test_null_content_returns_empty_string(self) -> None:
        text, _ = from_openai_message({"role": "assistant", "content": None})

        assert text == ""

    def test_parses_tool_calls(self) -> None:
        payload = {
            "role": "assistant",
            "content": None,
            "tool_calls": [
                {
                    "id": "call_1",
                    "type": "function",
                    "function": {
                        "name": "search",
                        "arguments": json.dumps({"q": "hi"}),
                    },
                },
            ],
        }

        text, calls = from_openai_message(payload)

        assert text == ""
        assert len(calls) == 1
        assert calls[0].call_id == "call_1"
        assert calls[0].tool_name == "search"
        assert calls[0].arguments == {"q": "hi"}

    def test_tool_call_with_empty_arguments_string(self) -> None:
        payload = {
            "tool_calls": [
                {
                    "id": "c1",
                    "function": {"name": "ping", "arguments": ""},
                },
            ],
        }

        _, calls = from_openai_message(payload)

        assert calls[0].arguments == {}

    def test_tool_call_with_invalid_json_arguments(self) -> None:
        payload = {
            "tool_calls": [
                {
                    "id": "c1",
                    "function": {"name": "ping", "arguments": "not-json"},
                },
            ],
        }

        _, calls = from_openai_message(payload)

        assert calls[0].arguments == {}

    def test_tool_call_without_function_name_is_skipped(self) -> None:
        payload = {
            "tool_calls": [
                {"id": "c1", "function": {"arguments": "{}"}},
                {
                    "id": "c2",
                    "function": {"name": "ok", "arguments": "{}"},
                },
            ],
        }

        _, calls = from_openai_message(payload)

        assert len(calls) == 1
        assert calls[0].tool_name == "ok"

    def test_non_list_tool_calls_returns_empty_tuple(self) -> None:
        _, calls = from_openai_message({"tool_calls": "nope"})

        assert calls == ()
