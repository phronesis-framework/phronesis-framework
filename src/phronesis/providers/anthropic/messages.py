"""Convert phronesis messages to/from the Anthropic message format.

Anthropic's API (v1/messages) takes:
- ``system`` as a top-level string (not a message),
- ``messages`` as an alternating sequence of ``user``/``assistant`` turns,
- content as either a plain string or a list of typed blocks:
  ``text``, ``tool_use``, ``tool_result``.

Reference: https://docs.anthropic.com/en/api/messages
"""

from __future__ import annotations

import json
from collections.abc import Sequence
from typing import Any

from phronesis.providers.types import Message, Role, ToolCall


def _text_block(text: str) -> dict[str, Any]:
    return {"type": "text", "text": text}


def _tool_use_block(call: ToolCall) -> dict[str, Any]:
    return {
        "type": "tool_use",
        "id": call.call_id,
        "name": call.tool_name,
        "input": call.arguments,
    }


def _tool_result_block(message: Message) -> dict[str, Any]:
    raw_output = message.tool_output
    content = raw_output if isinstance(raw_output, str) else json.dumps(raw_output)

    return {
        "type": "tool_result",
        "tool_use_id": message.tool_call_id or "",
        "content": content,
    }


def _assistant_blocks(message: Message) -> list[dict[str, Any]]:
    blocks: list[dict[str, Any]] = []

    if message.content:
        blocks.append(_text_block(message.content))

    for call in message.tool_calls:
        blocks.append(_tool_use_block(call))

    return blocks


def to_anthropic_messages(
    messages: Sequence[Message],
) -> tuple[list[dict[str, Any]], str | None]:
    """Translate ``messages`` into the Anthropic request shape.

    Returns a pair ``(messages, system)`` where ``messages`` is the value
    of the ``messages`` field and ``system`` is the value of the
    ``system`` field (``None`` if there are no system messages).
    Consecutive system messages are joined with two newlines.
    """
    system_chunks: list[str] = []
    out: list[dict[str, Any]] = []

    for message in messages:
        if message.role is Role.SYSTEM:
            if message.content:
                system_chunks.append(message.content)
            continue

        if message.role is Role.USER:
            out.append({"role": "user", "content": [_text_block(message.content)]})
            continue

        if message.role is Role.ASSISTANT:
            blocks = _assistant_blocks(message)
            out.append({"role": "assistant", "content": blocks})
            continue

        if message.role is Role.TOOL:
            out.append({"role": "user", "content": [_tool_result_block(message)]})

    system = "\n\n".join(system_chunks) if system_chunks else None

    return out, system


def from_anthropic_content(blocks: Sequence[dict[str, Any]]) -> tuple[str, tuple[ToolCall, ...]]:
    """Parse the ``content`` of an Anthropic ``message`` response.

    Returns the concatenated text and the tuple of tool calls extracted
    from ``tool_use`` blocks.
    """
    text_parts: list[str] = []
    calls: list[ToolCall] = []

    for block in blocks:
        block_type = block.get("type")

        if block_type == "text":
            text = block.get("text", "")

            if isinstance(text, str):
                text_parts.append(text)

            continue

        if block_type == "tool_use":
            raw_input = block.get("input", {})
            arguments = raw_input if isinstance(raw_input, dict) else {}
            calls.append(
                ToolCall(
                    call_id=str(block.get("id", "")),
                    tool_name=str(block.get("name", "")),
                    arguments=arguments,
                )
            )

    return "".join(text_parts), tuple(calls)
