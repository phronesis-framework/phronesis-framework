"""OpenAI Server-Sent Events streaming.

OpenAI's chat completions stream emits ``data: {json}`` SSE frames and
a terminal ``data: [DONE]`` sentinel. Tool calls are streamed across
many delta chunks indexed by ``index``; arguments arrive as partial
JSON strings that must be concatenated and parsed once the call closes.

Retry is intentionally *not* applied to streaming.
"""

from __future__ import annotations

import json
from collections.abc import AsyncIterator
from typing import Any

import httpx

from phronesis.providers.chunks import (
    Finish,
    LLMChunk,
    TextChunk,
    ToolCallEnd,
    ToolCallStart,
)
from phronesis.providers.errors import StreamError
from phronesis.providers.openai.errors import translate_response_error
from phronesis.providers.usage import TokenUsage

_DONE_SENTINEL = "[DONE]"


async def stream_openai_chat(
    http: httpx.AsyncClient,
    *,
    api_key: str,
    body: dict[str, Any],
) -> AsyncIterator[LLMChunk]:
    """POST a streaming chat completion and yield :data:`LLMChunk` values.

    Args:
        http: Pre-built :class:`httpx.AsyncClient`. Lifetime is the
            caller's responsibility.
        api_key: OpenAI API key for the ``Authorization`` header.
        body: JSON body. ``stream`` is forced to ``True`` and
            ``stream_options.include_usage`` is enabled so the terminal
            chunk carries usage information.

    Raises:
        ProviderError: For any HTTP 4xx/5xx response.
        StreamError: For malformed SSE frames or tool argument JSON.
    """
    request_body = _enable_streaming(body)
    headers = {
        "authorization": f"Bearer {api_key}",
        "content-type": "application/json",
        "accept": "text/event-stream",
    }

    async with http.stream(
        "POST", "/v1/chat/completions", json=request_body, headers=headers
    ) as response:
        if response.status_code >= 400:
            await response.aread()
            raise translate_response_error(response)

        async for chunk in _translate_chunks(_parse_sse(response)):
            yield chunk


def _enable_streaming(body: dict[str, Any]) -> dict[str, Any]:
    request_body = {**body, "stream": True}
    stream_options = request_body.get("stream_options")

    if isinstance(stream_options, dict):
        request_body["stream_options"] = {**stream_options, "include_usage": True}
    else:
        request_body["stream_options"] = {"include_usage": True}

    return request_body


async def _parse_sse(response: httpx.Response) -> AsyncIterator[dict[str, Any]]:
    async for line in response.aiter_lines():
        if not line or line.startswith(":"):
            continue

        if not line.startswith("data:"):
            continue

        payload = line[5:].lstrip()

        if payload == _DONE_SENTINEL:
            return

        try:
            yield json.loads(payload)
        except json.JSONDecodeError as exc:
            raise StreamError(f"Invalid SSE JSON payload: {payload!r}") from exc


async def _translate_chunks(
    chunks: AsyncIterator[dict[str, Any]],
) -> AsyncIterator[LLMChunk]:
    tool_buffers: dict[int, _ToolBuffer] = {}
    finish_reason = ""
    usage: TokenUsage | None = None
    saw_choices = False

    async for chunk in chunks:
        usage = _maybe_usage(chunk, usage)
        choices = chunk.get("choices")

        if not isinstance(choices, list) or not choices:
            continue

        saw_choices = True
        choice = choices[0]

        if not isinstance(choice, dict):
            continue

        for emitted in _process_choice(choice, tool_buffers):
            yield emitted

        raw_reason = choice.get("finish_reason")

        if isinstance(raw_reason, str) and raw_reason:
            finish_reason = raw_reason

    for emitted in _flush_tool_buffers(tool_buffers):
        yield emitted

    if saw_choices or usage is not None:
        yield Finish(reason=finish_reason, usage=usage)


def _maybe_usage(
    chunk: dict[str, Any],
    existing: TokenUsage | None,
) -> TokenUsage | None:
    raw = chunk.get("usage")

    if not isinstance(raw, dict):
        return existing

    prompt_details = raw.get("prompt_tokens_details")
    cache_read = prompt_details.get("cached_tokens") if isinstance(prompt_details, dict) else None

    return TokenUsage(
        input_tokens=_pick_int(raw.get("prompt_tokens")),
        output_tokens=_pick_int(raw.get("completion_tokens")),
        cache_read_tokens=_pick_int(cache_read),
        cache_creation_tokens=None,
    )


def _process_choice(
    choice: dict[str, Any],
    tool_buffers: dict[int, _ToolBuffer],
) -> list[LLMChunk]:
    emitted: list[LLMChunk] = []
    delta = choice.get("delta")

    if not isinstance(delta, dict):
        return emitted

    content = delta.get("content")

    if isinstance(content, str) and content:
        emitted.append(TextChunk(text=content))

    raw_calls = delta.get("tool_calls")

    if isinstance(raw_calls, list):
        for raw_call in raw_calls:
            extra = _absorb_tool_delta(raw_call, tool_buffers)

            if extra is not None:
                emitted.append(extra)

    return emitted


def _absorb_tool_delta(
    raw: Any,
    tool_buffers: dict[int, _ToolBuffer],
) -> LLMChunk | None:
    if not isinstance(raw, dict):
        return None

    index = raw.get("index")

    if not isinstance(index, int):
        return None

    raw_function = raw.get("function")
    function: dict[str, Any] = raw_function if isinstance(raw_function, dict) else {}
    started: LLMChunk | None = None
    buffer = tool_buffers.get(index)
    raw_name = function.get("name")
    raw_id = raw.get("id")

    if buffer is None:
        call_id = str(raw_id) if raw_id else ""
        tool_name = str(raw_name) if raw_name else ""
        buffer = _ToolBuffer(call_id=call_id, tool_name=tool_name)
        tool_buffers[index] = buffer
        started = ToolCallStart(call_id=call_id, tool_name=tool_name)
    else:
        if not buffer.call_id and raw_id:
            buffer.call_id = str(raw_id)

        if not buffer.tool_name and raw_name:
            buffer.tool_name = str(raw_name)

    arguments_part = function.get("arguments")

    if isinstance(arguments_part, str):
        buffer.json_parts.append(arguments_part)

    return started


def _flush_tool_buffers(tool_buffers: dict[int, _ToolBuffer]) -> list[LLMChunk]:
    emitted: list[LLMChunk] = []

    for index in sorted(tool_buffers.keys()):
        buffer = tool_buffers[index]
        raw_json = "".join(buffer.json_parts) or "{}"

        try:
            arguments = json.loads(raw_json)
        except json.JSONDecodeError as exc:
            raise StreamError(
                f"Invalid tool_call arguments JSON for {buffer.call_id!r}: {raw_json!r}",
            ) from exc

        if not isinstance(arguments, dict):
            arguments = {"value": arguments}

        emitted.append(ToolCallEnd(call_id=buffer.call_id, arguments=arguments))

    tool_buffers.clear()

    return emitted


def _pick_int(value: Any) -> int | None:
    return value if isinstance(value, int) else None


class _ToolBuffer:
    """Mutable per-index buffer for an in-progress streamed tool call."""

    __slots__ = ("call_id", "json_parts", "tool_name")

    def __init__(self, *, call_id: str, tool_name: str) -> None:
        self.call_id = call_id
        self.tool_name = tool_name
        self.json_parts: list[str] = []
