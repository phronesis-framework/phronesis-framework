"""Tests for ``phronesis.providers.openai.streaming``."""

from __future__ import annotations

import json
from typing import Any

import httpx
import pytest

from phronesis.providers.chunks import (
    Finish,
    LLMChunk,
    TextChunk,
    ToolCallEnd,
    ToolCallStart,
)
from phronesis.providers.errors import AuthenticationError, RateLimitError, StreamError
from phronesis.providers.openai.streaming import stream_openai_chat


def _sse(chunks: list[dict[str, Any]], *, done: bool = True) -> bytes:
    parts = [f"data: {json.dumps(chunk)}\n\n" for chunk in chunks]

    if done:
        parts.append("data: [DONE]\n\n")

    return "".join(parts).encode("utf-8")


def _make_client(body: bytes, status: int = 200) -> httpx.AsyncClient:
    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(
            status,
            content=body,
            headers={"content-type": "text/event-stream"},
        )

    transport = httpx.MockTransport(handler)

    return httpx.AsyncClient(transport=transport, base_url="https://api.openai.com")


async def _collect(iterator: Any) -> list[LLMChunk]:
    chunks: list[LLMChunk] = []

    async for chunk in iterator:
        chunks.append(chunk)

    return chunks


def _stream(
    client: httpx.AsyncClient,
    body: dict[str, Any] | None = None,
) -> Any:
    return stream_openai_chat(
        client,
        api_key="sk-test",
        body=body or {"model": "gpt-test", "messages": []},
    )


class TestStreamOpenaiChatTextEvents:
    @pytest.mark.asyncio
    async def test_yields_text_chunks_then_finish(self) -> None:
        events = [
            {"choices": [{"index": 0, "delta": {"content": "hello "}}]},
            {"choices": [{"index": 0, "delta": {"content": "world"}}]},
            {"choices": [{"index": 0, "delta": {}, "finish_reason": "stop"}]},
            {
                "choices": [],
                "usage": {"prompt_tokens": 5, "completion_tokens": 2},
            },
        ]
        client = _make_client(_sse(events))

        chunks = await _collect(_stream(client))

        assert chunks[0] == TextChunk(text="hello ")
        assert chunks[1] == TextChunk(text="world")
        assert isinstance(chunks[2], Finish)
        assert chunks[2].reason == "stop"
        assert chunks[2].usage is not None
        assert chunks[2].usage.input_tokens == 5
        assert chunks[2].usage.output_tokens == 2

    @pytest.mark.asyncio
    async def test_ignores_empty_content_deltas(self) -> None:
        events = [
            {"choices": [{"index": 0, "delta": {"content": ""}}]},
            {"choices": [{"index": 0, "delta": {}, "finish_reason": "stop"}]},
        ]
        client = _make_client(_sse(events))

        chunks = await _collect(_stream(client))

        assert chunks == [Finish(reason="stop", usage=None)]


class TestStreamOpenaiChatToolCalls:
    @pytest.mark.asyncio
    async def test_emits_tool_call_start_and_end(self) -> None:
        events = [
            {
                "choices": [
                    {
                        "index": 0,
                        "delta": {
                            "tool_calls": [
                                {
                                    "index": 0,
                                    "id": "call_1",
                                    "function": {"name": "search", "arguments": ""},
                                },
                            ],
                        },
                    },
                ],
            },
            {
                "choices": [
                    {
                        "index": 0,
                        "delta": {
                            "tool_calls": [
                                {"index": 0, "function": {"arguments": '{"q":'}},
                            ],
                        },
                    },
                ],
            },
            {
                "choices": [
                    {
                        "index": 0,
                        "delta": {
                            "tool_calls": [
                                {"index": 0, "function": {"arguments": '"hi"}'}},
                            ],
                        },
                    },
                ],
            },
            {"choices": [{"index": 0, "delta": {}, "finish_reason": "tool_calls"}]},
        ]
        client = _make_client(_sse(events))

        chunks = await _collect(_stream(client))

        assert chunks[0] == ToolCallStart(call_id="call_1", tool_name="search")
        assert chunks[1] == ToolCallEnd(call_id="call_1", arguments={"q": "hi"})
        assert isinstance(chunks[2], Finish)
        assert chunks[2].reason == "tool_calls"

    @pytest.mark.asyncio
    async def test_multiple_parallel_tool_calls(self) -> None:
        events = [
            {
                "choices": [
                    {
                        "index": 0,
                        "delta": {
                            "tool_calls": [
                                {
                                    "index": 0,
                                    "id": "a",
                                    "function": {"name": "f1", "arguments": "{}"},
                                },
                                {
                                    "index": 1,
                                    "id": "b",
                                    "function": {"name": "f2", "arguments": "{}"},
                                },
                            ],
                        },
                    },
                ],
            },
            {"choices": [{"index": 0, "delta": {}, "finish_reason": "tool_calls"}]},
        ]
        client = _make_client(_sse(events))

        chunks = await _collect(_stream(client))

        starts = [c for c in chunks if isinstance(c, ToolCallStart)]
        ends = [c for c in chunks if isinstance(c, ToolCallEnd)]
        assert [s.tool_name for s in starts] == ["f1", "f2"]
        assert [e.call_id for e in ends] == ["a", "b"]

    @pytest.mark.asyncio
    async def test_invalid_tool_arguments_raises_stream_error(self) -> None:
        events = [
            {
                "choices": [
                    {
                        "index": 0,
                        "delta": {
                            "tool_calls": [
                                {
                                    "index": 0,
                                    "id": "c1",
                                    "function": {"name": "f", "arguments": "not-json"},
                                },
                            ],
                        },
                    },
                ],
            },
            {"choices": [{"index": 0, "delta": {}, "finish_reason": "tool_calls"}]},
        ]
        client = _make_client(_sse(events))

        with pytest.raises(StreamError):
            await _collect(_stream(client))


class TestStreamOpenaiChatErrors:
    @pytest.mark.asyncio
    async def test_401_response_raises_authentication_error(self) -> None:
        body = json.dumps({"error": {"message": "bad key"}}).encode("utf-8")
        client = _make_client(body, status=401)

        with pytest.raises(AuthenticationError):
            await _collect(_stream(client))

    @pytest.mark.asyncio
    async def test_429_response_raises_rate_limit_error(self) -> None:
        body = json.dumps({"error": {"message": "slow"}}).encode("utf-8")
        client = _make_client(body, status=429)

        with pytest.raises(RateLimitError):
            await _collect(_stream(client))

    @pytest.mark.asyncio
    async def test_malformed_json_payload_raises_stream_error(self) -> None:
        body = b"data: not-json\n\n"
        client = _make_client(body)

        with pytest.raises(StreamError):
            await _collect(_stream(client))


class TestStreamOpenaiChatRequestShape:
    @pytest.mark.asyncio
    async def test_forces_stream_and_include_usage(self) -> None:
        captured: list[httpx.Request] = []

        def handler(request: httpx.Request) -> httpx.Response:
            captured.append(request)

            return httpx.Response(200, content=_sse([]))

        transport = httpx.MockTransport(handler)
        client = httpx.AsyncClient(transport=transport, base_url="https://api.openai.com")

        await _collect(
            _stream(client, body={"model": "gpt-test", "messages": [], "stream": False}),
        )

        sent = captured[0]
        body = json.loads(sent.content)
        assert body["stream"] is True
        assert body["stream_options"]["include_usage"] is True
        assert sent.url.path == "/v1/chat/completions"
        assert sent.headers["authorization"] == "Bearer sk-test"
        assert sent.headers["accept"] == "text/event-stream"

    @pytest.mark.asyncio
    async def test_done_sentinel_terminates_iteration(self) -> None:
        events = [
            {"choices": [{"index": 0, "delta": {"content": "ok"}}]},
            {"choices": [{"index": 0, "delta": {}, "finish_reason": "stop"}]},
        ]
        client = _make_client(_sse(events))

        chunks = await _collect(_stream(client))

        assert any(isinstance(c, TextChunk) for c in chunks)
        assert any(isinstance(c, Finish) for c in chunks)

    @pytest.mark.asyncio
    async def test_ignores_comment_and_blank_lines(self) -> None:
        body = (
            b":heartbeat\n\n"
            + _sse([{"choices": [{"index": 0, "delta": {"content": "ok"}}]}], done=False)
            + b"\n"
            + b"data: [DONE]\n\n"
        )
        client = _make_client(body)

        chunks = await _collect(_stream(client))

        assert chunks[0] == TextChunk(text="ok")
