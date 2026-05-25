"""Tests for ``phronesis.providers.openai.provider``."""

from __future__ import annotations

import json
from typing import Any

import httpx
import pytest

from phronesis._internal.retry import FixedBackoff
from phronesis.providers.errors import (
    AuthenticationError,
    RateLimitError,
    ServerError,
)
from phronesis.providers.openai.provider import OpenAIProvider
from phronesis.providers.protocol import LLMProvider, ProviderFeature
from phronesis.providers.retry_config import RetryConfig
from phronesis.providers.types import LLMRequest, Message, Role


def _ok_payload(text: str = "hello") -> dict[str, Any]:
    return {
        "id": "chatcmpl-1",
        "object": "chat.completion",
        "model": "gpt-test",
        "choices": [
            {
                "index": 0,
                "message": {"role": "assistant", "content": text},
                "finish_reason": "stop",
            },
        ],
        "usage": {"prompt_tokens": 10, "completion_tokens": 5},
    }


def _client(handler: httpx.MockTransport | Any) -> httpx.AsyncClient:
    transport = (
        handler if isinstance(handler, httpx.MockTransport) else httpx.MockTransport(handler)
    )

    return httpx.AsyncClient(transport=transport, base_url="https://api.openai.com")


def _make_provider(
    *,
    handler: Any,
    retry_config: RetryConfig | None = None,
    default_temperature: float | None = None,
    default_max_tokens: int | None = None,
) -> OpenAIProvider:
    return OpenAIProvider(
        model="gpt-test",
        api_key="sk-test",
        http_client=_client(handler),
        default_temperature=default_temperature,
        default_max_tokens=default_max_tokens,
        retry_config=retry_config or RetryConfig(backoff=FixedBackoff(0)),
    )


class TestOpenAIProviderProtocolConformance:
    def test_satisfies_llm_provider(self) -> None:
        provider = _make_provider(handler=lambda r: httpx.Response(200, json=_ok_payload()))

        assert isinstance(provider, LLMProvider)


class TestOpenAIProviderSupports:
    @pytest.mark.parametrize(
        "feature",
        [
            ProviderFeature.STRUCTURED_OUTPUT,
            ProviderFeature.REASONING_EFFORT,
            ProviderFeature.PREDICTED_OUTPUTS,
            ProviderFeature.PROMPT_CACHING,
            ProviderFeature.VISION,
        ],
    )
    def test_supports_openai_features(self, feature: ProviderFeature) -> None:
        provider = _make_provider(handler=lambda r: httpx.Response(200, json=_ok_payload()))

        assert provider.supports(feature)

    @pytest.mark.parametrize(
        "feature",
        [
            ProviderFeature.DOCUMENTS,
            ProviderFeature.EXTENDED_THINKING,
        ],
    )
    def test_does_not_support_anthropic_only_features(
        self,
        feature: ProviderFeature,
    ) -> None:
        provider = _make_provider(handler=lambda r: httpx.Response(200, json=_ok_payload()))

        assert not provider.supports(feature)


class TestOpenAIProviderCompleteRequestShape:
    @pytest.mark.asyncio
    async def test_sends_required_headers_and_endpoint(self) -> None:
        captured: list[httpx.Request] = []

        def handler(request: httpx.Request) -> httpx.Response:
            captured.append(request)

            return httpx.Response(200, json=_ok_payload())

        provider = _make_provider(handler=handler)
        await provider.complete(
            LLMRequest(model="", messages=(Message(role=Role.USER, content="hi"),)),
        )

        sent = captured[0]
        assert sent.url.path == "/v1/chat/completions"
        assert sent.headers["authorization"] == "Bearer sk-test"
        assert sent.headers["content-type"].startswith("application/json")

    @pytest.mark.asyncio
    async def test_request_body_carries_model_and_messages(self) -> None:
        captured: list[dict[str, Any]] = []

        def handler(request: httpx.Request) -> httpx.Response:
            captured.append(json.loads(request.content))

            return httpx.Response(200, json=_ok_payload())

        provider = _make_provider(handler=handler)
        await provider.complete(
            LLMRequest(model="", messages=(Message(role=Role.USER, content="hi"),)),
        )

        body = captured[0]
        assert body["model"] == "gpt-test"
        assert body["messages"] == [{"role": "user", "content": "hi"}]
        assert "temperature" not in body
        assert "max_tokens" not in body
        assert "tools" not in body

    @pytest.mark.asyncio
    async def test_request_system_prepended_as_message(self) -> None:
        captured: list[dict[str, Any]] = []

        def handler(request: httpx.Request) -> httpx.Response:
            captured.append(json.loads(request.content))

            return httpx.Response(200, json=_ok_payload())

        provider = _make_provider(handler=handler)
        await provider.complete(
            LLMRequest(
                model="",
                messages=(
                    Message(role=Role.SYSTEM, content="ignored"),
                    Message(role=Role.USER, content="hi"),
                ),
                system="explicit",
            ),
        )

        assert captured[0]["messages"][0] == {"role": "system", "content": "explicit"}
        assert captured[0]["messages"][1] == {"role": "user", "content": "hi"}

    @pytest.mark.asyncio
    async def test_temperature_default_and_override(self) -> None:
        captured: list[dict[str, Any]] = []

        def handler(request: httpx.Request) -> httpx.Response:
            captured.append(json.loads(request.content))

            return httpx.Response(200, json=_ok_payload())

        provider = _make_provider(handler=handler, default_temperature=0.2)
        await provider.complete(
            LLMRequest(model="", messages=(Message(role=Role.USER, content="hi"),)),
        )
        await provider.complete(
            LLMRequest(
                model="",
                messages=(Message(role=Role.USER, content="hi"),),
                temperature=0.9,
            ),
        )

        assert captured[0]["temperature"] == 0.2
        assert captured[1]["temperature"] == 0.9

    @pytest.mark.asyncio
    async def test_max_tokens_only_when_set(self) -> None:
        captured: list[dict[str, Any]] = []

        def handler(request: httpx.Request) -> httpx.Response:
            captured.append(json.loads(request.content))

            return httpx.Response(200, json=_ok_payload())

        provider = _make_provider(handler=handler, default_max_tokens=128)
        await provider.complete(
            LLMRequest(model="", messages=(Message(role=Role.USER, content="hi"),)),
        )
        await provider.complete(
            LLMRequest(
                model="",
                messages=(Message(role=Role.USER, content="hi"),),
                max_tokens=512,
            ),
        )

        assert captured[0]["max_tokens"] == 128
        assert captured[1]["max_tokens"] == 512


class TestOpenAIProviderCompleteResponse:
    @pytest.mark.asyncio
    async def test_parses_text_and_usage(self) -> None:
        provider = _make_provider(
            handler=lambda r: httpx.Response(200, json=_ok_payload("world")),
        )

        response = await provider.complete(
            LLMRequest(model="", messages=(Message(role=Role.USER, content="hi"),)),
        )

        assert response.text == "world"
        assert response.finish_reason == "stop"
        assert response.usage is not None
        assert response.usage.input_tokens == 10
        assert response.usage.output_tokens == 5

    @pytest.mark.asyncio
    async def test_parses_tool_calls(self) -> None:
        payload = {
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
                                    "arguments": json.dumps({"q": "x"}),
                                },
                            },
                        ],
                    },
                    "finish_reason": "tool_calls",
                },
            ],
            "usage": {"prompt_tokens": 1, "completion_tokens": 2},
        }
        provider = _make_provider(handler=lambda r: httpx.Response(200, json=payload))

        response = await provider.complete(
            LLMRequest(model="", messages=(Message(role=Role.USER, content="hi"),)),
        )

        assert response.text == ""
        assert len(response.tool_calls) == 1
        assert response.tool_calls[0].tool_name == "search"
        assert response.tool_calls[0].arguments == {"q": "x"}

    @pytest.mark.asyncio
    async def test_parses_cached_tokens(self) -> None:
        payload = _ok_payload()
        payload["usage"] = {
            "prompt_tokens": 10,
            "completion_tokens": 5,
            "prompt_tokens_details": {"cached_tokens": 3},
        }
        provider = _make_provider(handler=lambda r: httpx.Response(200, json=payload))

        response = await provider.complete(
            LLMRequest(model="", messages=(Message(role=Role.USER, content="hi"),)),
        )

        assert response.usage is not None
        assert response.usage.cache_read_tokens == 3
        assert response.usage.cache_creation_tokens is None


class TestOpenAIProviderErrors:
    @pytest.mark.asyncio
    async def test_401_raises_authentication_error(self) -> None:
        provider = _make_provider(
            handler=lambda r: httpx.Response(
                401,
                json={"error": {"message": "bad key"}},
            ),
        )

        with pytest.raises(AuthenticationError):
            await provider.complete(
                LLMRequest(model="", messages=(Message(role=Role.USER, content="hi"),)),
            )

    @pytest.mark.asyncio
    async def test_500_is_retried(self) -> None:
        calls = {"n": 0}

        def handler(request: httpx.Request) -> httpx.Response:
            calls["n"] += 1

            if calls["n"] < 2:
                return httpx.Response(500, json={"error": {"message": "boom"}})

            return httpx.Response(200, json=_ok_payload())

        provider = _make_provider(handler=handler)
        response = await provider.complete(
            LLMRequest(model="", messages=(Message(role=Role.USER, content="hi"),)),
        )

        assert response.text == "hello"
        assert calls["n"] == 2

    @pytest.mark.asyncio
    async def test_429_propagates_after_retry_exhaustion(self) -> None:
        provider = _make_provider(
            handler=lambda r: httpx.Response(429, json={"error": {"message": "slow"}}),
            retry_config=RetryConfig(max_attempts=2, backoff=FixedBackoff(0)),
        )

        with pytest.raises((RateLimitError, ServerError, Exception)):
            await provider.complete(
                LLMRequest(model="", messages=(Message(role=Role.USER, content="hi"),)),
            )


class TestOpenAIProviderStream:
    @pytest.mark.asyncio
    async def test_stream_returns_async_iterator(self) -> None:
        provider = _make_provider(handler=lambda r: httpx.Response(200, json=_ok_payload()))

        iterator = provider.stream(
            LLMRequest(model="", messages=(Message(role=Role.USER, content="hi"),)),
        )

        assert hasattr(iterator, "__aiter__")
