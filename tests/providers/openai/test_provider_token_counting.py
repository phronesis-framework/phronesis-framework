"""Tests for ``OpenAIProvider.count_tokens_exact``."""

from __future__ import annotations

from typing import Any

import httpx
import pytest

from phronesis._internal.retry import FixedBackoff
from phronesis.core.messages import TextBlock, UserMessage
from phronesis.providers.openai.provider import OpenAIProvider
from phronesis.providers.protocol import ProviderFeature
from phronesis.providers.retry_config import RetryConfig


def _client(handler: Any) -> httpx.AsyncClient:
    transport = httpx.MockTransport(handler)

    return httpx.AsyncClient(transport=transport, base_url="https://api.openai.com")


def _make_provider() -> OpenAIProvider:
    return OpenAIProvider(
        model="gpt-4o",
        api_key="sk-test",
        http_client=_client(lambda r: httpx.Response(200, json={})),
        retry_config=RetryConfig(backoff=FixedBackoff(0)),
    )


class TestNativeTokenCountFeature:
    def test_does_not_support_native_token_count(self) -> None:
        provider = _make_provider()

        assert provider.supports(ProviderFeature.NATIVE_TOKEN_COUNT) is False


class TestCountTokensExact:
    @pytest.mark.asyncio
    async def test_returns_none(self) -> None:
        provider = _make_provider()

        result = await provider.count_tokens_exact(
            [UserMessage(content=(TextBlock(text="hello"),))],
        )

        assert result is None
