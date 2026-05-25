"""Tests for ``phronesis.providers.anthropic.factory``."""

from __future__ import annotations

import httpx
import pytest

from phronesis.providers.anthropic.factory import anthropic
from phronesis.providers.anthropic.provider import AnthropicProvider
from phronesis.providers.errors import AuthenticationError


def _mock_client() -> httpx.AsyncClient:
    transport = httpx.MockTransport(lambda r: httpx.Response(200, json={}))

    return httpx.AsyncClient(transport=transport, base_url="https://api.anthropic.com")


class TestAnthropicFactory:
    def test_returns_provider_with_explicit_key(self) -> None:
        provider = anthropic("claude-test", api_key="sk-x", http_client=_mock_client())

        assert isinstance(provider, AnthropicProvider)
        assert provider.model == "claude-test"

    def test_reads_api_key_from_env(self, monkeypatch: pytest.MonkeyPatch) -> None:
        monkeypatch.setenv("ANTHROPIC_API_KEY", "sk-env")

        provider = anthropic("claude-test", http_client=_mock_client())

        assert isinstance(provider, AnthropicProvider)

    def test_explicit_key_takes_precedence_over_env(
        self,
        monkeypatch: pytest.MonkeyPatch,
    ) -> None:
        monkeypatch.setenv("ANTHROPIC_API_KEY", "sk-env")

        provider = anthropic(
            "claude-test",
            api_key="sk-explicit",
            http_client=_mock_client(),
        )

        assert provider._api_key == "sk-explicit"

    def test_missing_key_raises(self, monkeypatch: pytest.MonkeyPatch) -> None:
        monkeypatch.delenv("ANTHROPIC_API_KEY", raising=False)

        with pytest.raises(AuthenticationError):
            anthropic("claude-test", http_client=_mock_client())

    def test_propagates_default_temperature_and_max_tokens(self) -> None:
        provider = anthropic(
            "claude-test",
            api_key="sk-x",
            temperature=0.42,
            max_tokens=2048,
            http_client=_mock_client(),
        )

        assert provider._default_temperature == 0.42
        assert provider._default_max_tokens == 2048

    def test_default_http_client_created_when_omitted(
        self,
        monkeypatch: pytest.MonkeyPatch,
    ) -> None:
        monkeypatch.setenv("ANTHROPIC_API_KEY", "sk-x")

        provider = anthropic("claude-test", base_url="https://example.test", timeout=5.0)

        assert isinstance(provider._http, httpx.AsyncClient)
        assert str(provider._http.base_url) == "https://example.test"
