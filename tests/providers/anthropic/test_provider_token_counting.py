"""Tests for ``AnthropicProvider.count_tokens_exact``."""

from __future__ import annotations

from typing import Any

import httpx
import pytest

from phronesis._internal.retry import FixedBackoff
from phronesis.core.messages import SystemMessage, TextBlock, UserMessage
from phronesis.providers.anthropic.provider import AnthropicProvider
from phronesis.providers.errors import RateLimitError
from phronesis.providers.protocol import ProviderFeature
from phronesis.providers.retry_config import RetryConfig


def _client(handler: Any) -> httpx.AsyncClient:
    transport = httpx.MockTransport(handler)

    return httpx.AsyncClient(transport=transport, base_url="https://api.anthropic.com")


def _make_provider(*, handler: Any) -> AnthropicProvider:
    return AnthropicProvider(
        model="claude-test",
        api_key="sk-test",
        http_client=_client(handler),
        retry_config=RetryConfig(backoff=FixedBackoff(0)),
    )


class TestNativeTokenCountFeature:
    def test_supports_native_token_count(self) -> None:
        provider = _make_provider(handler=lambda r: httpx.Response(200, json={}))

        assert provider.supports(ProviderFeature.NATIVE_TOKEN_COUNT) is True


class TestCountTokensExact:
    @pytest.mark.asyncio
    async def test_returns_endpoint_value(self) -> None:
        captured: dict[str, Any] = {}

        def handler(request: httpx.Request) -> httpx.Response:
            captured["url"] = str(request.url)
            captured["body"] = request.read()
            return httpx.Response(200, json={"input_tokens": 42})

        provider = _make_provider(handler=handler)

        result = await provider.count_tokens_exact(
            [UserMessage(content=(TextBlock(text="hello"),))],
        )

        assert result == 42
        assert "/v1/messages/count_tokens" in captured["url"]

    @pytest.mark.asyncio
    async def test_includes_system_when_present(self) -> None:
        import json

        captured: dict[str, Any] = {}

        def handler(request: httpx.Request) -> httpx.Response:
            captured["body"] = json.loads(request.read())
            return httpx.Response(200, json={"input_tokens": 17})

        provider = _make_provider(handler=handler)

        await provider.count_tokens_exact(
            [
                SystemMessage(content=(TextBlock(text="be helpful"),)),
                UserMessage(content=(TextBlock(text="hi"),)),
            ],
        )

        assert captured["body"]["system"] == "be helpful"
        assert captured["body"]["messages"][0]["role"] == "user"

    @pytest.mark.asyncio
    async def test_returns_none_when_payload_missing_field(self) -> None:
        provider = _make_provider(
            handler=lambda r: httpx.Response(200, json={"unexpected": "shape"}),
        )

        result = await provider.count_tokens_exact(
            [UserMessage(content=(TextBlock(text="hello"),))],
        )

        assert result is None

    @pytest.mark.asyncio
    async def test_returns_none_when_payload_not_object(self) -> None:
        provider = _make_provider(
            handler=lambda r: httpx.Response(200, json=["unexpected"]),
        )

        result = await provider.count_tokens_exact(
            [UserMessage(content=(TextBlock(text="hello"),))],
        )

        assert result is None

    @pytest.mark.asyncio
    async def test_translates_errors(self) -> None:
        provider = _make_provider(
            handler=lambda r: httpx.Response(
                429,
                json={"error": {"type": "rate_limit_error", "message": "slow down"}},
            ),
        )

        with pytest.raises(RateLimitError):
            await provider.count_tokens_exact(
                [UserMessage(content=(TextBlock(text="hi"),))],
            )
