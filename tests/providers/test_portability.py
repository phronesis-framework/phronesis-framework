"""Cross-provider portability tests.

These tests assert that built-in providers expose the same observable
contract: same request types in, same response shape out. They use
:class:`httpx.MockTransport` per-provider to simulate canonical
responses and tool flows, with no real network I/O.
"""

from __future__ import annotations

import json
from collections.abc import Callable
from dataclasses import dataclass
from typing import Any

import httpx
import pytest

from phronesis._internal.retry import FixedBackoff
from phronesis._internal.retry.exceptions import RetryExhaustedError
from phronesis.providers.anthropic.provider import AnthropicProvider
from phronesis.providers.chunks import Finish, LLMChunk, TextChunk, ToolCallEnd, ToolCallStart
from phronesis.providers.errors import (
    AuthenticationError,
    BadRequestError,
    RateLimitError,
    ServerError,
)
from phronesis.providers.openai.provider import OpenAIProvider
from phronesis.providers.protocol import LLMProvider, ProviderFeature
from phronesis.providers.retry_config import RetryConfig
from phronesis.providers.types import LLMRequest, LLMResponse, Message, Role

# --- handler builders --------------------------------------------------


def _anthropic_text_payload(text: str = "hi") -> dict[str, Any]:
    return {
        "id": "msg_1",
        "type": "message",
        "role": "assistant",
        "model": "claude-test",
        "content": [{"type": "text", "text": text}],
        "stop_reason": "end_turn",
        "usage": {"input_tokens": 3, "output_tokens": 2},
    }


def _openai_text_payload(text: str = "hi") -> dict[str, Any]:
    return {
        "id": "chatcmpl-1",
        "choices": [
            {
                "index": 0,
                "message": {"role": "assistant", "content": text},
                "finish_reason": "stop",
            }
        ],
        "usage": {"prompt_tokens": 3, "completion_tokens": 2},
    }


def _anthropic_tool_payload() -> dict[str, Any]:
    return {
        "id": "msg_1",
        "type": "message",
        "role": "assistant",
        "model": "claude-test",
        "content": [
            {
                "type": "tool_use",
                "id": "call_1",
                "name": "search",
                "input": {"q": "hi"},
            }
        ],
        "stop_reason": "tool_use",
        "usage": {"input_tokens": 1, "output_tokens": 1},
    }


def _openai_tool_payload() -> dict[str, Any]:
    return {
        "choices": [
            {
                "message": {
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
                        }
                    ],
                },
                "finish_reason": "tool_calls",
            }
        ],
        "usage": {"prompt_tokens": 1, "completion_tokens": 1},
    }


def _anthropic_sse(events: list[dict[str, Any]]) -> bytes:
    parts: list[str] = []

    for event in events:
        parts.append(f"event: {event['type']}\n")
        parts.append(f"data: {json.dumps(event)}\n\n")

    return "".join(parts).encode("utf-8")


def _openai_sse(events: list[dict[str, Any]]) -> bytes:
    parts = [f"data: {json.dumps(chunk)}\n\n" for chunk in events]
    parts.append("data: [DONE]\n\n")

    return "".join(parts).encode("utf-8")


# --- fixtures ----------------------------------------------------------


@dataclass(frozen=True)
class _ProviderCase:
    """A built-in provider plus its canned response payloads."""

    name: str
    build: Callable[[Any], Any]
    text_response: Callable[[str], httpx.Response]
    tool_response: Callable[[], httpx.Response]
    stream_text: Callable[[], bytes]
    error_response: Callable[[int], httpx.Response]


def _build_anthropic(handler: Any) -> AnthropicProvider:
    transport = (
        handler if isinstance(handler, httpx.MockTransport) else httpx.MockTransport(handler)
    )
    client = httpx.AsyncClient(transport=transport, base_url="https://api.anthropic.com")

    return AnthropicProvider(
        model="claude-test",
        api_key="sk-test",
        http_client=client,
        retry_config=RetryConfig(backoff=FixedBackoff(0)),
    )


def _build_openai(handler: Any) -> OpenAIProvider:
    transport = (
        handler if isinstance(handler, httpx.MockTransport) else httpx.MockTransport(handler)
    )
    client = httpx.AsyncClient(transport=transport, base_url="https://api.openai.com")

    return OpenAIProvider(
        model="gpt-test",
        api_key="sk-test",
        http_client=client,
        retry_config=RetryConfig(backoff=FixedBackoff(0)),
    )


def _anthropic_text_stream() -> bytes:
    return _anthropic_sse(
        [
            {"type": "content_block_start", "index": 0, "content_block": {"type": "text"}},
            {
                "type": "content_block_delta",
                "index": 0,
                "delta": {"type": "text_delta", "text": "hi"},
            },
            {"type": "content_block_stop", "index": 0},
            {
                "type": "message_delta",
                "delta": {"stop_reason": "end_turn"},
                "usage": {"input_tokens": 1, "output_tokens": 1},
            },
            {"type": "message_stop"},
        ]
    )


def _openai_text_stream() -> bytes:
    return _openai_sse(
        [
            {"choices": [{"index": 0, "delta": {"content": "hi"}}]},
            {"choices": [{"index": 0, "delta": {}, "finish_reason": "stop"}]},
        ]
    )


def _anthropic_error(status: int) -> httpx.Response:
    body = {"error": {"type": "authentication_error", "message": "bad"}}

    if status == 429:
        body = {"error": {"type": "rate_limit_error", "message": "slow"}}
    elif status >= 500:
        body = {"error": {"type": "api_error", "message": "boom"}}
    elif status == 400:
        body = {"error": {"type": "invalid_request_error", "message": "bad arg"}}

    return httpx.Response(status, json=body)


def _openai_error(status: int) -> httpx.Response:
    return httpx.Response(status, json={"error": {"message": "err"}})


_PROVIDERS = [
    _ProviderCase(
        name="anthropic",
        build=_build_anthropic,
        text_response=lambda text: httpx.Response(200, json=_anthropic_text_payload(text)),
        tool_response=lambda: httpx.Response(200, json=_anthropic_tool_payload()),
        stream_text=_anthropic_text_stream,
        error_response=_anthropic_error,
    ),
    _ProviderCase(
        name="openai",
        build=_build_openai,
        text_response=lambda text: httpx.Response(200, json=_openai_text_payload(text)),
        tool_response=lambda: httpx.Response(200, json=_openai_tool_payload()),
        stream_text=_openai_text_stream,
        error_response=_openai_error,
    ),
]


@pytest.fixture(params=_PROVIDERS, ids=lambda case: case.name)
def case(request: pytest.FixtureRequest) -> _ProviderCase:
    value: _ProviderCase = request.param

    return value


# --- helpers -----------------------------------------------------------


def _simple_request() -> LLMRequest:
    return LLMRequest(
        model="",
        messages=(Message(role=Role.USER, content="hi"),),
    )


async def _collect(iterator: Any) -> list[LLMChunk]:
    out: list[LLMChunk] = []

    async for chunk in iterator:
        out.append(chunk)

    return out


# --- tests -------------------------------------------------------------


class TestProtocolConformance:
    def test_provider_satisfies_protocol(self, case: _ProviderCase) -> None:
        provider = case.build(lambda r: case.text_response("hi"))

        assert isinstance(provider, LLMProvider)


class TestSharedFeatureSupport:
    def test_prompt_caching_supported_everywhere(self, case: _ProviderCase) -> None:
        provider = case.build(lambda r: case.text_response("hi"))

        assert provider.supports(ProviderFeature.PROMPT_CACHING)

    def test_vision_supported_everywhere(self, case: _ProviderCase) -> None:
        provider = case.build(lambda r: case.text_response("hi"))

        assert provider.supports(ProviderFeature.VISION)


class TestCompleteUniformShape:
    @pytest.mark.asyncio
    async def test_text_response_carries_text_and_usage(self, case: _ProviderCase) -> None:
        provider = case.build(lambda r: case.text_response("hello"))

        response = await provider.complete(_simple_request())

        assert isinstance(response, LLMResponse)
        assert response.text == "hello"
        assert response.finish_reason != ""
        assert response.usage is not None
        assert response.usage.input_tokens == 3
        assert response.usage.output_tokens == 2

    @pytest.mark.asyncio
    async def test_tool_call_uniform(self, case: _ProviderCase) -> None:
        provider = case.build(lambda r: case.tool_response())

        response = await provider.complete(_simple_request())

        assert len(response.tool_calls) == 1
        call = response.tool_calls[0]
        assert call.tool_name == "search"
        assert call.arguments == {"q": "hi"}


class TestStreamUniformShape:
    @pytest.mark.asyncio
    async def test_text_stream_yields_text_then_finish(self, case: _ProviderCase) -> None:
        body = case.stream_text()

        def handler(_: httpx.Request) -> httpx.Response:
            return httpx.Response(200, content=body, headers={"content-type": "text/event-stream"})

        provider = case.build(handler)
        chunks = await _collect(provider.stream(_simple_request()))

        text_chunks = [c for c in chunks if isinstance(c, TextChunk)]
        assert text_chunks
        assert "".join(c.text for c in text_chunks) == "hi"
        assert isinstance(chunks[-1], Finish)

    @pytest.mark.asyncio
    async def test_stream_chunks_match_sealed_union(self, case: _ProviderCase) -> None:
        body = case.stream_text()

        def handler(_: httpx.Request) -> httpx.Response:
            return httpx.Response(200, content=body, headers={"content-type": "text/event-stream"})

        provider = case.build(handler)
        chunks = await _collect(provider.stream(_simple_request()))

        for chunk in chunks:
            assert isinstance(chunk, TextChunk | ToolCallStart | ToolCallEnd | Finish)


class TestUniformErrorMapping:
    @pytest.mark.asyncio
    async def test_401_raises_authentication_error(self, case: _ProviderCase) -> None:
        provider = case.build(lambda r: case.error_response(401))

        with pytest.raises(AuthenticationError):
            await provider.complete(_simple_request())

    @pytest.mark.asyncio
    async def test_429_raises_rate_limit_error(self, case: _ProviderCase) -> None:
        provider = case.build(lambda r: case.error_response(429))

        with pytest.raises(RetryExhaustedError) as exc_info:
            await provider.complete(_simple_request())

        assert isinstance(exc_info.value.last_exception, RateLimitError)

    @pytest.mark.asyncio
    async def test_400_raises_bad_request(self, case: _ProviderCase) -> None:
        provider = case.build(lambda r: case.error_response(400))

        with pytest.raises(BadRequestError):
            await provider.complete(_simple_request())

    @pytest.mark.asyncio
    async def test_5xx_is_retried_then_succeeds(self, case: _ProviderCase) -> None:
        calls = {"n": 0}

        def handler(_: httpx.Request) -> httpx.Response:
            calls["n"] += 1

            if calls["n"] < 2:
                return case.error_response(500)

            return case.text_response("ok")

        provider = case.build(handler)
        response = await provider.complete(_simple_request())

        assert response.text == "ok"
        assert calls["n"] == 2

    @pytest.mark.asyncio
    async def test_5xx_propagates_after_exhaustion(self, case: _ProviderCase) -> None:
        provider = case.build(lambda r: case.error_response(500))

        with pytest.raises(RetryExhaustedError) as exc_info:
            await provider.complete(_simple_request())

        assert isinstance(exc_info.value.last_exception, ServerError)
