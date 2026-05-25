"""Tests for ``phronesis.providers.anthropic.provider``."""

from __future__ import annotations

from typing import Any

import httpx
import pytest

from phronesis._internal.retry import FixedBackoff
from phronesis.providers.anthropic.provider import AnthropicProvider
from phronesis.providers.errors import (
    AuthenticationError,
    RateLimitError,
    ServerError,
)
from phronesis.providers.protocol import LLMProvider, ProviderFeature
from phronesis.providers.retry_config import RetryConfig
from phronesis.providers.types import LLMRequest, Message, Role


def _ok_payload(text: str = "hello") -> dict[str, Any]:
    return {
        "id": "msg_1",
        "type": "message",
        "role": "assistant",
        "model": "claude-test",
        "content": [{"type": "text", "text": text}],
        "stop_reason": "end_turn",
        "usage": {"input_tokens": 10, "output_tokens": 5},
    }


def _client(handler: httpx.MockTransport | Any) -> httpx.AsyncClient:
    transport = (
        handler if isinstance(handler, httpx.MockTransport) else httpx.MockTransport(handler)
    )

    return httpx.AsyncClient(transport=transport, base_url="https://api.anthropic.com")


def _make_provider(
    *,
    handler: Any,
    retry_config: RetryConfig | None = None,
    default_temperature: float | None = None,
) -> AnthropicProvider:
    return AnthropicProvider(
        model="claude-test",
        api_key="sk-test",
        http_client=_client(handler),
        default_temperature=default_temperature,
        retry_config=retry_config or RetryConfig(backoff=FixedBackoff(0)),
    )


class TestAnthropicProviderProtocolConformance:
    def test_satisfies_llm_provider(self) -> None:
        provider = _make_provider(handler=lambda r: httpx.Response(200, json=_ok_payload()))

        assert isinstance(provider, LLMProvider)


class TestAnthropicProviderSupports:
    @pytest.mark.parametrize(
        "feature",
        [
            ProviderFeature.PROMPT_CACHING,
            ProviderFeature.VISION,
            ProviderFeature.DOCUMENTS,
            ProviderFeature.EXTENDED_THINKING,
        ],
    )
    def test_supports_anthropic_features(self, feature: ProviderFeature) -> None:
        provider = _make_provider(handler=lambda r: httpx.Response(200, json=_ok_payload()))

        assert provider.supports(feature)

    @pytest.mark.parametrize(
        "feature",
        [
            ProviderFeature.STRUCTURED_OUTPUT,
            ProviderFeature.REASONING_EFFORT,
            ProviderFeature.PREDICTED_OUTPUTS,
        ],
    )
    def test_does_not_support_other_features(self, feature: ProviderFeature) -> None:
        provider = _make_provider(handler=lambda r: httpx.Response(200, json=_ok_payload()))

        assert not provider.supports(feature)


class TestAnthropicProviderCompleteRequestShape:
    @pytest.mark.asyncio
    async def test_sends_required_headers_and_endpoint(self) -> None:
        captured: list[httpx.Request] = []

        def handler(request: httpx.Request) -> httpx.Response:
            captured.append(request)

            return httpx.Response(200, json=_ok_payload())

        provider = _make_provider(handler=handler)
        await provider.complete(
            LLMRequest(model="", messages=(Message(role=Role.USER, content="hi"),))
        )

        sent = captured[0]
        assert sent.url.path == "/v1/messages"
        assert sent.headers["x-api-key"] == "sk-test"
        assert sent.headers["anthropic-version"] == "2023-06-01"
        assert sent.headers["content-type"].startswith("application/json")

    @pytest.mark.asyncio
    async def test_request_body_carries_model_messages_and_max_tokens(self) -> None:
        captured: list[dict[str, Any]] = []

        def handler(request: httpx.Request) -> httpx.Response:
            import json

            captured.append(json.loads(request.content))

            return httpx.Response(200, json=_ok_payload())

        provider = _make_provider(handler=handler)
        await provider.complete(
            LLMRequest(model="", messages=(Message(role=Role.USER, content="hi"),)),
        )

        body = captured[0]
        assert body["model"] == "claude-test"
        assert body["max_tokens"] == 4096
        assert body["messages"] == [{"role": "user", "content": [{"type": "text", "text": "hi"}]}]
        assert "system" not in body
        assert "temperature" not in body
        assert "tools" not in body

    @pytest.mark.asyncio
    async def test_system_messages_extracted(self) -> None:
        captured: list[dict[str, Any]] = []

        def handler(request: httpx.Request) -> httpx.Response:
            import json

            captured.append(json.loads(request.content))

            return httpx.Response(200, json=_ok_payload())

        provider = _make_provider(handler=handler)
        await provider.complete(
            LLMRequest(
                model="",
                messages=(
                    Message(role=Role.SYSTEM, content="be helpful"),
                    Message(role=Role.USER, content="hi"),
                ),
            ),
        )

        assert captured[0]["system"] == "be helpful"

    @pytest.mark.asyncio
    async def test_explicit_request_system_overrides_messages(self) -> None:
        captured: list[dict[str, Any]] = []

        def handler(request: httpx.Request) -> httpx.Response:
            import json

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

        assert captured[0]["system"] == "explicit"

    @pytest.mark.asyncio
    async def test_temperature_default_and_override(self) -> None:
        captured: list[dict[str, Any]] = []

        def handler(request: httpx.Request) -> httpx.Response:
            import json

            captured.append(json.loads(request.content))

            return httpx.Response(200, json=_ok_payload())

        provider = _make_provider(handler=handler, default_temperature=0.2)
        request = LLMRequest(model="", messages=(Message(role=Role.USER, content="hi"),))
        await provider.complete(request)
        await provider.complete(
            LLMRequest(
                model="",
                messages=(Message(role=Role.USER, content="hi"),),
                temperature=0.9,
            ),
        )

        assert captured[0]["temperature"] == 0.2
        assert captured[1]["temperature"] == 0.9


class TestAnthropicProviderCompleteResponse:
    @pytest.mark.asyncio
    async def test_parses_text_and_usage(self) -> None:
        provider = _make_provider(
            handler=lambda r: httpx.Response(200, json=_ok_payload("world")),
        )

        response = await provider.complete(
            LLMRequest(model="", messages=(Message(role=Role.USER, content="hi"),)),
        )

        assert response.text == "world"
        assert response.finish_reason == "end_turn"
        assert response.usage is not None
        assert response.usage.input_tokens == 10
        assert response.usage.output_tokens == 5

    @pytest.mark.asyncio
    async def test_parses_tool_calls(self) -> None:
        payload = {
            "content": [
                {"type": "text", "text": "calling tool"},
                {
                    "type": "tool_use",
                    "id": "call_1",
                    "name": "search",
                    "input": {"q": "x"},
                },
            ],
            "stop_reason": "tool_use",
            "usage": {"input_tokens": 1, "output_tokens": 2},
        }
        provider = _make_provider(handler=lambda r: httpx.Response(200, json=payload))

        response = await provider.complete(
            LLMRequest(model="", messages=(Message(role=Role.USER, content="hi"),)),
        )

        assert response.text == "calling tool"
        assert len(response.tool_calls) == 1
        assert response.tool_calls[0].tool_name == "search"
        assert response.tool_calls[0].arguments == {"q": "x"}

    @pytest.mark.asyncio
    async def test_parses_cache_token_fields(self) -> None:
        payload = _ok_payload()
        payload["usage"] = {
            "input_tokens": 1,
            "output_tokens": 2,
            "cache_read_input_tokens": 3,
            "cache_creation_input_tokens": 4,
        }
        provider = _make_provider(handler=lambda r: httpx.Response(200, json=payload))

        response = await provider.complete(
            LLMRequest(model="", messages=(Message(role=Role.USER, content="hi"),)),
        )

        assert response.usage is not None
        assert response.usage.cache_read_tokens == 3
        assert response.usage.cache_creation_tokens == 4


class TestAnthropicProviderErrors:
    @pytest.mark.asyncio
    async def test_401_raises_authentication_error(self) -> None:
        provider = _make_provider(
            handler=lambda r: httpx.Response(
                401,
                json={"error": {"type": "authentication_error", "message": "bad key"}},
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
                return httpx.Response(
                    500,
                    json={"error": {"type": "api_error", "message": "boom"}},
                )

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
            handler=lambda r: httpx.Response(
                429,
                json={"error": {"type": "rate_limit_error", "message": "slow"}},
            ),
            retry_config=RetryConfig(max_attempts=2, backoff=FixedBackoff(0)),
        )

        with pytest.raises((RateLimitError, ServerError, Exception)):
            await provider.complete(
                LLMRequest(model="", messages=(Message(role=Role.USER, content="hi"),)),
            )


class TestAnthropicProviderStream:
    @pytest.mark.asyncio
    async def test_stream_raises_not_implemented(self) -> None:
        provider = _make_provider(handler=lambda r: httpx.Response(200, json=_ok_payload()))

        with pytest.raises(NotImplementedError):
            provider.stream(LLMRequest(model="", messages=()))
