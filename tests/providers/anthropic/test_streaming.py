"""Tests for ``phronesis.providers.anthropic.streaming``."""

from __future__ import annotations

import json
from collections.abc import Iterable
from typing import Any

import httpx
import pytest

from phronesis.providers.anthropic.streaming import stream_anthropic_messages
from phronesis.providers.chunks import (
    Finish,
    LLMChunk,
    TextChunk,
    ToolCallEnd,
    ToolCallStart,
)
from phronesis.providers.errors import (
    AuthenticationError,
    RateLimitError,
    StreamError,
)


def _sse(events: Iterable[Any]) -> bytes:
    """Build raw SSE bytes from a list of event payloads."""
    parts: list[str] = []

    for event in events:
        parts.append(f"event: {event['type']}\n")
        parts.append(f"data: {json.dumps(event)}\n\n")

    return "".join(parts).encode("utf-8")


def _make_client(body: bytes, status: int = 200) -> httpx.AsyncClient:
    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(
            status,
            content=body,
            headers={"content-type": "text/event-stream"},
        )

    transport = httpx.MockTransport(handler)

    return httpx.AsyncClient(transport=transport, base_url="https://api.anthropic.com")


async def _collect(iterator: Any) -> list[LLMChunk]:
    chunks: list[LLMChunk] = []

    async for chunk in iterator:
        chunks.append(chunk)

    return chunks


def _stream(
    client: httpx.AsyncClient,
    body: dict[str, Any] | None = None,
) -> Any:
    return stream_anthropic_messages(
        client,
        api_key="sk-test",
        api_version="2023-06-01",
        body=body or {"model": "claude-test", "messages": []},
    )


class TestStreamAnthropicMessagesTextEvents:
    @pytest.mark.asyncio
    async def test_yields_text_chunks_then_finish(self) -> None:
        events = [
            {"type": "message_start", "message": {}},
            {"type": "content_block_start", "index": 0, "content_block": {"type": "text"}},
            {
                "type": "content_block_delta",
                "index": 0,
                "delta": {"type": "text_delta", "text": "hello "},
            },
            {
                "type": "content_block_delta",
                "index": 0,
                "delta": {"type": "text_delta", "text": "world"},
            },
            {"type": "content_block_stop", "index": 0},
            {
                "type": "message_delta",
                "delta": {"stop_reason": "end_turn"},
                "usage": {"input_tokens": 5, "output_tokens": 2},
            },
            {"type": "message_stop"},
        ]
        client = _make_client(_sse(events))

        chunks = await _collect(_stream(client))

        assert chunks[0] == TextChunk(text="hello ")
        assert chunks[1] == TextChunk(text="world")
        assert isinstance(chunks[2], Finish)
        assert chunks[2].reason == "end_turn"
        assert chunks[2].usage is not None
        assert chunks[2].usage.input_tokens == 5
        assert chunks[2].usage.output_tokens == 2

    @pytest.mark.asyncio
    async def test_ignores_empty_text_deltas(self) -> None:
        events = [
            {
                "type": "content_block_delta",
                "index": 0,
                "delta": {"type": "text_delta", "text": ""},
            },
            {"type": "message_stop"},
        ]
        client = _make_client(_sse(events))

        chunks = await _collect(_stream(client))

        assert chunks == [Finish(reason="", usage=None)]


class TestStreamAnthropicMessagesToolUse:
    @pytest.mark.asyncio
    async def test_emits_tool_call_start_and_end(self) -> None:
        events = [
            {
                "type": "content_block_start",
                "index": 0,
                "content_block": {"type": "tool_use", "id": "call_1", "name": "search"},
            },
            {
                "type": "content_block_delta",
                "index": 0,
                "delta": {"type": "input_json_delta", "partial_json": '{"q":'},
            },
            {
                "type": "content_block_delta",
                "index": 0,
                "delta": {"type": "input_json_delta", "partial_json": '"hi"}'},
            },
            {"type": "content_block_stop", "index": 0},
            {"type": "message_stop"},
        ]
        client = _make_client(_sse(events))

        chunks = await _collect(_stream(client))

        assert chunks[0] == ToolCallStart(call_id="call_1", tool_name="search")
        assert chunks[1] == ToolCallEnd(call_id="call_1", arguments={"q": "hi"})
        assert isinstance(chunks[2], Finish)

    @pytest.mark.asyncio
    async def test_empty_tool_input_defaults_to_empty_dict(self) -> None:
        events = [
            {
                "type": "content_block_start",
                "index": 0,
                "content_block": {"type": "tool_use", "id": "call_x", "name": "ping"},
            },
            {"type": "content_block_stop", "index": 0},
            {"type": "message_stop"},
        ]
        client = _make_client(_sse(events))

        chunks = await _collect(_stream(client))

        assert chunks[0] == ToolCallStart(call_id="call_x", tool_name="ping")
        assert chunks[1] == ToolCallEnd(call_id="call_x", arguments={})

    @pytest.mark.asyncio
    async def test_invalid_tool_input_raises_stream_error(self) -> None:
        events = [
            {
                "type": "content_block_start",
                "index": 0,
                "content_block": {"type": "tool_use", "id": "call_1", "name": "search"},
            },
            {
                "type": "content_block_delta",
                "index": 0,
                "delta": {"type": "input_json_delta", "partial_json": "not-json"},
            },
            {"type": "content_block_stop", "index": 0},
        ]
        client = _make_client(_sse(events))

        with pytest.raises(StreamError):
            await _collect(_stream(client))


class TestStreamAnthropicMessagesMixedContent:
    @pytest.mark.asyncio
    async def test_text_then_tool_call_in_order(self) -> None:
        events = [
            {"type": "content_block_start", "index": 0, "content_block": {"type": "text"}},
            {
                "type": "content_block_delta",
                "index": 0,
                "delta": {"type": "text_delta", "text": "thinking"},
            },
            {"type": "content_block_stop", "index": 0},
            {
                "type": "content_block_start",
                "index": 1,
                "content_block": {"type": "tool_use", "id": "c2", "name": "lookup"},
            },
            {
                "type": "content_block_delta",
                "index": 1,
                "delta": {"type": "input_json_delta", "partial_json": '{"k":1}'},
            },
            {"type": "content_block_stop", "index": 1},
            {"type": "message_delta", "delta": {"stop_reason": "tool_use"}},
            {"type": "message_stop"},
        ]
        client = _make_client(_sse(events))

        chunks = await _collect(_stream(client))

        assert chunks[0] == TextChunk(text="thinking")
        assert chunks[1] == ToolCallStart(call_id="c2", tool_name="lookup")
        assert chunks[2] == ToolCallEnd(call_id="c2", arguments={"k": 1})
        assert isinstance(chunks[3], Finish)
        assert chunks[3].reason == "tool_use"


class TestStreamAnthropicMessagesErrors:
    @pytest.mark.asyncio
    async def test_error_event_raises_stream_error(self) -> None:
        events = [
            {
                "type": "error",
                "error": {"type": "overloaded_error", "message": "try again"},
            },
        ]
        client = _make_client(_sse(events))

        with pytest.raises(StreamError) as exc_info:
            await _collect(_stream(client))

        assert "try again" in str(exc_info.value)

    @pytest.mark.asyncio
    async def test_401_response_raises_authentication_error(self) -> None:
        body = json.dumps(
            {"error": {"type": "authentication_error", "message": "bad key"}},
        ).encode("utf-8")
        client = _make_client(body, status=401)

        with pytest.raises(AuthenticationError):
            await _collect(_stream(client))

    @pytest.mark.asyncio
    async def test_429_response_raises_rate_limit_error(self) -> None:
        body = json.dumps(
            {"error": {"type": "rate_limit_error", "message": "slow"}},
        ).encode("utf-8")
        client = _make_client(body, status=429)

        with pytest.raises(RateLimitError):
            await _collect(_stream(client))

    @pytest.mark.asyncio
    async def test_malformed_json_payload_raises_stream_error(self) -> None:
        body = b"event: message_start\ndata: not-json\n\n"
        client = _make_client(body)

        with pytest.raises(StreamError):
            await _collect(_stream(client))


class TestStreamAnthropicMessagesRequestShape:
    @pytest.mark.asyncio
    async def test_forces_stream_true_and_sends_headers(self) -> None:
        captured: list[httpx.Request] = []

        def handler(request: httpx.Request) -> httpx.Response:
            captured.append(request)

            return httpx.Response(200, content=_sse([{"type": "message_stop"}]))

        transport = httpx.MockTransport(handler)
        client = httpx.AsyncClient(transport=transport, base_url="https://api.anthropic.com")

        await _collect(
            _stream(client, body={"model": "claude-test", "messages": [], "stream": False}),
        )

        sent = captured[0]
        body = json.loads(sent.content)
        assert body["stream"] is True
        assert sent.url.path == "/v1/messages"
        assert sent.headers["x-api-key"] == "sk-test"
        assert sent.headers["anthropic-version"] == "2023-06-01"
        assert sent.headers["accept"] == "text/event-stream"

    @pytest.mark.asyncio
    async def test_ignores_sse_comments_and_unknown_events(self) -> None:
        events = [
            {"type": "ping"},
            {
                "type": "content_block_delta",
                "index": 0,
                "delta": {"type": "text_delta", "text": "ok"},
            },
            {"type": "message_stop"},
        ]
        body = b":heartbeat\n\n" + _sse(events)
        client = _make_client(body)

        chunks = await _collect(_stream(client))

        assert chunks[0] == TextChunk(text="ok")
        assert isinstance(chunks[1], Finish)
