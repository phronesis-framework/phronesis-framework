"""Message conversion for the OpenAI provider.

See ``docs/PROVIDERS-DECISIONS.md``. OpenAI's Chat Completions API uses
a flat ``messages`` list where ``system`` appears as a regular entry,
``assistant`` may carry ``tool_calls`` (whose arguments are JSON-encoded
strings), and tool outputs use ``role: tool`` with ``tool_call_id``.
"""

from __future__ import annotations

import json
from collections.abc import Iterable
from typing import Any

from phronesis.providers.types import Message, Role, ToolCall


def to_openai_messages(messages: Iterable[Message]) -> list[dict[str, Any]]:
    """Convert framework :class:`Message` instances to OpenAI dicts."""
    return [_message_to_dict(message) for message in messages]


def from_openai_message(payload: dict[str, Any]) -> tuple[str, tuple[ToolCall, ...]]:
    """Extract assistant text and tool calls from a response message dict."""
    text = _string_or_empty(payload.get("content"))
    raw_calls = payload.get("tool_calls")

    if not isinstance(raw_calls, list):
        return text, ()

    tool_calls = tuple(
        call for call in (_tool_call_from_dict(item) for item in raw_calls) if call is not None
    )

    return text, tool_calls


def _message_to_dict(message: Message) -> dict[str, Any]:
    if message.role is Role.ASSISTANT:
        return _assistant_to_dict(message)

    if message.role is Role.TOOL:
        return _tool_to_dict(message)

    return {"role": str(message.role), "content": message.content}


def _assistant_to_dict(message: Message) -> dict[str, Any]:
    payload: dict[str, Any] = {"role": "assistant", "content": message.content or None}

    if message.tool_calls:
        payload["tool_calls"] = [_tool_call_to_dict(call) for call in message.tool_calls]

    return payload


def _tool_to_dict(message: Message) -> dict[str, Any]:
    content = _tool_output_to_str(message.tool_output, fallback=message.content)

    return {
        "role": "tool",
        "tool_call_id": message.tool_call_id or "",
        "content": content,
    }


def _tool_call_to_dict(call: ToolCall) -> dict[str, Any]:
    return {
        "id": call.call_id,
        "type": "function",
        "function": {
            "name": call.tool_name,
            "arguments": json.dumps(call.arguments),
        },
    }


def _tool_call_from_dict(item: Any) -> ToolCall | None:
    if not isinstance(item, dict):
        return None

    function = item.get("function")

    if not isinstance(function, dict):
        return None

    name = function.get("name")

    if not isinstance(name, str) or not name:
        return None

    arguments = _decode_arguments(function.get("arguments"))

    return ToolCall(
        call_id=str(item.get("id", "")),
        tool_name=name,
        arguments=arguments,
    )


def _decode_arguments(raw: Any) -> dict[str, Any]:
    if isinstance(raw, dict):
        return raw

    if not isinstance(raw, str) or not raw:
        return {}

    try:
        decoded = json.loads(raw)
    except json.JSONDecodeError:
        return {}

    if isinstance(decoded, dict):
        return decoded

    return {}


def _string_or_empty(value: Any) -> str:
    return value if isinstance(value, str) else ""


def _tool_output_to_str(output: Any, *, fallback: str) -> str:
    if output is None:
        return fallback

    if isinstance(output, str):
        return output

    try:
        return json.dumps(output)
    except (TypeError, ValueError):
        return str(output)
