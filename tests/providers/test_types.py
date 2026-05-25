"""Tests for ``phronesis.providers.types``."""

from __future__ import annotations

import dataclasses

import pytest

from phronesis.providers.types import LLMRequest, LLMResponse, Message, Role, ToolCall
from phronesis.providers.usage import TokenUsage


class TestRole:
    def test_values_are_lowercase_strings(self) -> None:
        assert Role.SYSTEM.value == "system"
        assert Role.USER.value == "user"
        assert Role.ASSISTANT.value == "assistant"
        assert Role.TOOL.value == "tool"

    def test_role_is_str_subclass(self) -> None:
        assert isinstance(Role.USER, str)
        assert str(Role.USER) == "user"


class TestToolCall:
    def test_holds_fields(self) -> None:
        call = ToolCall(call_id="c1", tool_name="search", arguments={"q": "x"})

        assert call.call_id == "c1"
        assert call.tool_name == "search"
        assert call.arguments == {"q": "x"}

    def test_is_frozen(self) -> None:
        call = ToolCall(call_id="c", tool_name="t", arguments={})

        with pytest.raises(dataclasses.FrozenInstanceError):
            call.call_id = "other"  # type: ignore[misc]


class TestMessage:
    def test_user_message_minimal(self) -> None:
        msg = Message(role=Role.USER, content="hi")

        assert msg.role is Role.USER
        assert msg.content == "hi"
        assert msg.tool_calls == ()
        assert msg.tool_call_id is None
        assert msg.tool_output is None

    def test_assistant_message_with_tool_calls(self) -> None:
        call = ToolCall(call_id="c1", tool_name="t", arguments={})
        msg = Message(role=Role.ASSISTANT, tool_calls=(call,))

        assert msg.content == ""
        assert msg.tool_calls == (call,)

    def test_tool_message_carries_output_and_id(self) -> None:
        msg = Message(role=Role.TOOL, tool_call_id="c1", tool_output={"ok": True})

        assert msg.tool_call_id == "c1"
        assert msg.tool_output == {"ok": True}


class TestLLMRequest:
    def test_minimal_construction(self) -> None:
        request = LLMRequest(model="x", messages=(Message(role=Role.USER, content="hi"),))

        assert request.model == "x"
        assert len(request.messages) == 1
        assert request.tools == ()
        assert request.system is None
        assert request.temperature is None
        assert request.max_tokens is None
        assert request.metadata == {}

    def test_metadata_default_is_independent_per_instance(self) -> None:
        a = LLMRequest(model="x", messages=())
        b = LLMRequest(model="y", messages=())

        assert a.metadata is not b.metadata

    def test_is_frozen(self) -> None:
        request = LLMRequest(model="x", messages=())

        with pytest.raises(dataclasses.FrozenInstanceError):
            request.model = "y"  # type: ignore[misc]


class TestLLMResponse:
    def test_default_construction(self) -> None:
        response = LLMResponse()

        assert response.text == ""
        assert response.tool_calls == ()
        assert response.finish_reason == ""
        assert response.usage is None

    def test_carries_usage(self) -> None:
        usage = TokenUsage(input_tokens=1)
        response = LLMResponse(text="ok", usage=usage)

        assert response.usage is usage
