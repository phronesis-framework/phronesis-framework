"""Convert phronesis messages to/from the Anthropic message format.

The Anthropic ``/v1/messages`` endpoint takes:

* ``system`` as a top-level string (not a message in the list);
* ``messages`` as an alternating sequence of ``user``/``assistant``
  turns;
* content as either a plain string or a list of typed blocks
  (``text``, ``tool_use``, ``tool_result``).

This module hides those shape rules behind two helpers,
:func:`to_anthropic_messages` (outbound) and
:func:`from_anthropic_content` (inbound), so the rest of the
framework can stay in :class:`Message`/:class:`ToolCall` land.
"""

from __future__ import annotations

import json
from collections.abc import Sequence
from typing import Any

from phronesis.providers.types import MediaRef, Message, Role, ToolCall


def _text_block(text: str) -> dict[str, Any]:
    return {"type": "text", "text": text}


def _ephemeral_cache_control() -> dict[str, str]:
    return {"type": "ephemeral"}


def _mark_cached(block: dict[str, Any]) -> dict[str, Any]:
    return {**block, "cache_control": _ephemeral_cache_control()}


def _media_block(ref: MediaRef) -> dict[str, Any]:
    source: dict[str, Any] = (
        {"type": "url", "url": ref.data}
        if ref.source_type == "url"
        else {"type": "base64", "media_type": ref.media_type, "data": ref.data}
    )

    return {
        "type": "image" if ref.kind == "image" else "document",
        "source": source,
    }


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
) -> tuple[list[dict[str, Any]], str | list[dict[str, Any]] | None]:
    """Translate ``messages`` into the Anthropic request shape.

    System messages are extracted from the sequence and joined into
    the top-level ``system`` field. When no system chunk is cached
    the field is a plain string (two-newline join); when at least
    one chunk carries a cache hint the field is a list of typed
    text blocks so the per-chunk ``cache_control`` marker survives
    serialisation. Tool result messages are folded into ``user``
    turns whose only block is a ``tool_result`` block.

    Messages whose ``cache`` flag is ``True`` get a
    ``cache_control: {"type": "ephemeral"}`` marker on the **last**
    block of their translated content, opting the prefix up to and
    including the message into Anthropic's prompt cache.

    Args:
        messages: Conversation history in framework form.

    Returns:
        A ``(messages, system)`` pair: ``messages`` is the value of
        the ``messages`` field in the request body and ``system`` is
        the value of the ``system`` field (``None`` when there are
        no system messages, plain string when no caching is
        requested, list of blocks otherwise).
    """
    system_chunks: list[tuple[str, bool]] = []
    out: list[dict[str, Any]] = []

    for message in messages:
        if message.role is Role.SYSTEM:
            if message.content:
                system_chunks.append((message.content, message.cache))
            continue

        if message.role is Role.USER:
            blocks: list[dict[str, Any]] = []

            if message.content:
                blocks.append(_text_block(message.content))

            blocks.extend(_media_block(ref) for ref in message.media)

            if not blocks:
                blocks.append(_text_block(""))

            if message.cache:
                blocks[-1] = _mark_cached(blocks[-1])

            out.append({"role": "user", "content": blocks})
            continue

        if message.role is Role.ASSISTANT:
            assistant_blocks = _assistant_blocks(message)

            if message.cache and assistant_blocks:
                assistant_blocks[-1] = _mark_cached(assistant_blocks[-1])

            out.append({"role": "assistant", "content": assistant_blocks})
            continue

        if message.role is Role.TOOL:
            tool_blocks: list[dict[str, Any]] = [_tool_result_block(message)]

            if message.cache and tool_blocks:
                tool_blocks[-1] = _mark_cached(tool_blocks[-1])

            out.append({"role": "user", "content": tool_blocks})

    system = _build_system(system_chunks)

    return out, system


def _build_system(
    chunks: list[tuple[str, bool]],
) -> str | list[dict[str, Any]] | None:
    """Build the Anthropic ``system`` field from ``chunks``.

    Returns a plain string when no chunk is cached (back-compat
    fast path), or a list of typed text blocks when at least one
    chunk carries a cache hint. Returns ``None`` when there are
    no system chunks.
    """
    if not chunks:
        return None

    if not any(cache for _, cache in chunks):
        return "\n\n".join(text for text, _ in chunks)

    blocks: list[dict[str, Any]] = []

    for text, cache in chunks:
        block = _text_block(text)

        if cache:
            block = _mark_cached(block)

        blocks.append(block)

    return blocks


def from_anthropic_content(blocks: Sequence[dict[str, Any]]) -> tuple[str, tuple[ToolCall, ...]]:
    """Parse the ``content`` of an Anthropic message response.

    Args:
        blocks: List of typed content blocks as returned by the
            Anthropic API.

    Returns:
        A ``(text, tool_calls)`` pair where ``text`` is the
        concatenated content of every ``text`` block and
        ``tool_calls`` is the tuple of :class:`ToolCall` instances
        derived from every ``tool_use`` block.
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
