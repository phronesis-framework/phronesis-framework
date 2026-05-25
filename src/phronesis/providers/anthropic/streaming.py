"""Anthropic Server-Sent Events streaming.

See ``docs/PROVIDERS-DECISIONS.md`` (D-08, D-12). Anthropic's
``/v1/messages?stream=true`` returns an SSE stream of typed events. This
module parses that stream and translates it into the framework-level
:data:`phronesis.providers.chunks.LLMChunk` union.

Retry is intentionally *not* applied here: see D-12. ``complete`` retries
the whole request, but mid-stream recovery is out of scope.
"""

from __future__ import annotations

import json
from collections.abc import AsyncIterator
from typing import Any

import httpx

from phronesis.providers.anthropic.errors import translate_response_error
from phronesis.providers.chunks import (
    Finish,
    LLMChunk,
    TextChunk,
    ToolCallEnd,
    ToolCallStart,
)
from phronesis.providers.errors import StreamError
from phronesis.providers.usage import TokenUsage


async def stream_anthropic_messages(
    http: httpx.AsyncClient,
    *,
    api_key: str,
    api_version: str,
    body: dict[str, Any],
) -> AsyncIterator[LLMChunk]:
    """POST a streaming ``/v1/messages`` request and yield :data:`LLMChunk`.

    Args:
        http: Pre-built :class:`httpx.AsyncClient`. Lifetime is the
            caller's responsibility.
        api_key: Anthropic API key for the ``x-api-key`` header.
        api_version: Value for ``anthropic-version``.
        body: JSON body for the request. ``stream`` is forced to ``True``.

    Raises:
        ProviderError: For any HTTP 4xx/5xx response.
        StreamError: For malformed SSE frames or ``error`` events.
    """
    request_body = {**body, "stream": True}
    headers = {
        "x-api-key": api_key,
        "anthropic-version": api_version,
        "content-type": "application/json",
        "accept": "text/event-stream",
    }

    async with http.stream("POST", "/v1/messages", json=request_body, headers=headers) as response:
        if response.status_code >= 400:
            await response.aread()
            raise translate_response_error(response)

        async for chunk in _translate_events(_parse_sse(response)):
            yield chunk


async def _parse_sse(response: httpx.Response) -> AsyncIterator[dict[str, Any]]:
    """Yield decoded JSON payloads from an SSE response.

    Anthropic's SSE frames look like::

        event: message_start
        data: {"type": "message_start", ...}

    Frames are terminated by a blank line. Only the ``data:`` payload is
    meaningful here; the ``event:`` line is informational and the
    embedded ``type`` field is authoritative.
    """
    data_lines: list[str] = []

    async for line in response.aiter_lines():
        if line == "":
            if data_lines:
                payload = "\n".join(data_lines)
                data_lines = []

                try:
                    yield json.loads(payload)
                except json.JSONDecodeError as exc:
                    raise StreamError(f"Invalid SSE JSON payload: {payload!r}") from exc

            continue

        if line.startswith(":"):
            continue

        if line.startswith("data:"):
            data_lines.append(line[5:].lstrip())

    if data_lines:
        payload = "\n".join(data_lines)

        try:
            yield json.loads(payload)
        except json.JSONDecodeError as exc:
            raise StreamError(f"Invalid SSE JSON payload: {payload!r}") from exc


async def _translate_events(
    events: AsyncIterator[dict[str, Any]],
) -> AsyncIterator[LLMChunk]:
    """Translate Anthropic stream events into :data:`LLMChunk` values."""
    tool_buffers: dict[int, _ToolBuffer] = {}
    stop_reason = ""
    usage: TokenUsage | None = None

    async for event in events:
        event_type = event.get("type")

        if event_type == "error":
            raise _build_stream_error(event)

        if event_type == "content_block_start":
            chunk = _handle_block_start(event, tool_buffers)

            if chunk is not None:
                yield chunk

            continue

        if event_type == "content_block_delta":
            chunk = _handle_block_delta(event, tool_buffers)

            if chunk is not None:
                yield chunk

            continue

        if event_type == "content_block_stop":
            chunk = _handle_block_stop(event, tool_buffers)

            if chunk is not None:
                yield chunk

            continue

        if event_type == "message_delta":
            stop_reason, usage = _absorb_message_delta(event, stop_reason, usage)

            continue

        if event_type == "message_stop":
            yield Finish(reason=stop_reason, usage=usage)

            return


class _ToolBuffer:
    """Mutable per-block buffer for an in-progress tool_use block."""

    __slots__ = ("call_id", "json_parts", "tool_name")

    def __init__(self, call_id: str, tool_name: str) -> None:
        self.call_id = call_id
        self.tool_name = tool_name
        self.json_parts: list[str] = []


def _handle_block_start(
    event: dict[str, Any],
    tool_buffers: dict[int, _ToolBuffer],
) -> LLMChunk | None:
    block = event.get("content_block")
    index = event.get("index")

    if not isinstance(block, dict) or not isinstance(index, int):
        return None

    if block.get("type") != "tool_use":
        return None

    call_id = str(block.get("id", ""))
    tool_name = str(block.get("name", ""))
    tool_buffers[index] = _ToolBuffer(call_id, tool_name)

    return ToolCallStart(call_id=call_id, tool_name=tool_name)


def _handle_block_delta(
    event: dict[str, Any],
    tool_buffers: dict[int, _ToolBuffer],
) -> LLMChunk | None:
    delta = event.get("delta")
    index = event.get("index")

    if not isinstance(delta, dict):
        return None

    delta_type = delta.get("type")

    if delta_type == "text_delta":
        text = delta.get("text")

        if isinstance(text, str) and text:
            return TextChunk(text=text)

        return None

    if delta_type == "input_json_delta" and isinstance(index, int):
        partial = delta.get("partial_json")
        buffer = tool_buffers.get(index)

        if buffer is not None and isinstance(partial, str):
            buffer.json_parts.append(partial)

    return None


def _handle_block_stop(
    event: dict[str, Any],
    tool_buffers: dict[int, _ToolBuffer],
) -> LLMChunk | None:
    index = event.get("index")

    if not isinstance(index, int):
        return None

    buffer = tool_buffers.pop(index, None)

    if buffer is None:
        return None

    raw_json = "".join(buffer.json_parts) or "{}"

    try:
        arguments = json.loads(raw_json)
    except json.JSONDecodeError as exc:
        raise StreamError(
            f"Invalid tool_use input JSON for call {buffer.call_id!r}: {raw_json!r}",
        ) from exc

    if not isinstance(arguments, dict):
        arguments = {"value": arguments}

    return ToolCallEnd(call_id=buffer.call_id, arguments=arguments)


def _absorb_message_delta(
    event: dict[str, Any],
    stop_reason: str,
    usage: TokenUsage | None,
) -> tuple[str, TokenUsage | None]:
    delta = event.get("delta")

    if isinstance(delta, dict):
        raw_reason = delta.get("stop_reason")

        if isinstance(raw_reason, str):
            stop_reason = raw_reason

    raw_usage = event.get("usage")

    if isinstance(raw_usage, dict):
        usage = _merge_usage(usage, raw_usage)

    return stop_reason, usage


def _merge_usage(existing: TokenUsage | None, raw: dict[str, Any]) -> TokenUsage:
    base = existing or TokenUsage()

    return TokenUsage(
        input_tokens=_pick_int(raw.get("input_tokens"), base.input_tokens),
        output_tokens=_pick_int(raw.get("output_tokens"), base.output_tokens),
        cache_read_tokens=_pick_int(raw.get("cache_read_input_tokens"), base.cache_read_tokens),
        cache_creation_tokens=_pick_int(
            raw.get("cache_creation_input_tokens"), base.cache_creation_tokens
        ),
    )


def _pick_int(value: Any, fallback: int | None) -> int | None:
    return value if isinstance(value, int) else fallback


def _build_stream_error(event: dict[str, Any]) -> StreamError:
    error = event.get("error")

    if isinstance(error, dict):
        message = error.get("message") or error.get("type") or "stream error"

        return StreamError(str(message))

    return StreamError("stream error")
