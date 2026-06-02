"""Tests for ``phronesis.providers.openai.helpers`` (OSS factories)."""

from __future__ import annotations

import httpx
import pytest

from phronesis.providers.errors import AuthenticationError
from phronesis.providers.openai.helpers import ollama, openwebui, vllm
from phronesis.providers.openai.provider import OpenAIProvider
from phronesis.providers.protocol import ProviderFeature


def _mock_client(base_url: str) -> httpx.AsyncClient:
    transport = httpx.MockTransport(lambda r: httpx.Response(200, json={}))

    return httpx.AsyncClient(transport=transport, base_url=base_url)


class TestOllamaFactory:
    def test_default_host_yields_v1_base_url(self) -> None:
        provider = ollama(
            "qwen2.5",
            http_client=_mock_client("http://localhost:11434/v1"),
        )

        assert isinstance(provider, OpenAIProvider)
        assert provider.model == "qwen2.5"
        assert provider._api_key == ""

    def test_strips_trailing_slash_from_host(self) -> None:
        provider = ollama(
            "qwen2.5",
            host="http://localhost:11434/",
            http_client=_mock_client("http://localhost:11434/v1"),
        )

        assert provider._api_key == ""

    def test_default_features_only_structured_output(self) -> None:
        provider = ollama(
            "qwen2.5",
            http_client=_mock_client("http://localhost:11434/v1"),
        )

        assert provider.supports(ProviderFeature.STRUCTURED_OUTPUT)
        assert not provider.supports(ProviderFeature.VISION)
        assert not provider.supports(ProviderFeature.REASONING_EFFORT)

    def test_context_window_resolved_from_oss_table(self) -> None:
        provider = ollama(
            "qwen2.5",
            http_client=_mock_client("http://localhost:11434/v1"),
        )

        assert provider.context_window_size() == 128_000

    def test_features_override(self) -> None:
        provider = ollama(
            "qwen2.5",
            features=frozenset({ProviderFeature.VISION}),
            http_client=_mock_client("http://localhost:11434/v1"),
        )

        assert provider.supports(ProviderFeature.VISION)
        assert not provider.supports(ProviderFeature.STRUCTURED_OUTPUT)

    def test_context_window_override(self) -> None:
        provider = ollama(
            "qwen2.5",
            context_window=4096,
            http_client=_mock_client("http://localhost:11434/v1"),
        )

        assert provider.context_window_size() == 4096


class TestVllmFactory:
    def test_no_api_key_yields_empty_key(self) -> None:
        provider = vllm(
            "Qwen/Qwen2.5-7B-Instruct",
            base_url="http://gpu-box:8000",
            http_client=_mock_client("http://gpu-box:8000"),
        )

        assert isinstance(provider, OpenAIProvider)
        assert provider._api_key == ""

    def test_explicit_api_key_propagates(self) -> None:
        provider = vllm(
            "Qwen/Qwen2.5-7B-Instruct",
            base_url="http://gpu-box:8000",
            api_key="token-xyz",
            http_client=_mock_client("http://gpu-box:8000"),
        )

        assert provider._api_key == "token-xyz"

    def test_default_features_only_structured_output(self) -> None:
        provider = vllm(
            "Qwen/Qwen2.5-7B-Instruct",
            base_url="http://gpu-box:8000",
            http_client=_mock_client("http://gpu-box:8000"),
        )

        assert provider.supports(ProviderFeature.STRUCTURED_OUTPUT)
        assert not provider.supports(ProviderFeature.PROMPT_CACHING)

    def test_features_and_context_window_override(self) -> None:
        provider = vllm(
            "Qwen/Qwen2.5-7B-Instruct",
            base_url="http://gpu-box:8000",
            features=frozenset({ProviderFeature.VISION}),
            context_window=65_536,
            http_client=_mock_client("http://gpu-box:8000"),
        )

        assert provider.supports(ProviderFeature.VISION)
        assert provider.context_window_size() == 65_536


class TestOpenWebUIFactory:
    def test_missing_key_raises(self, monkeypatch: pytest.MonkeyPatch) -> None:
        monkeypatch.delenv("OPENWEBUI_API_KEY", raising=False)

        with pytest.raises(AuthenticationError):
            openwebui(
                "gpt-4o",
                base_url="http://owui/api",
                http_client=_mock_client("http://owui/api"),
            )

    def test_reads_key_from_env(self, monkeypatch: pytest.MonkeyPatch) -> None:
        monkeypatch.setenv("OPENWEBUI_API_KEY", "jwt-env")

        provider = openwebui(
            "gpt-4o",
            base_url="http://owui/api",
            http_client=_mock_client("http://owui/api"),
        )

        assert provider._api_key == "jwt-env"

    def test_explicit_key_takes_precedence(
        self,
        monkeypatch: pytest.MonkeyPatch,
    ) -> None:
        monkeypatch.setenv("OPENWEBUI_API_KEY", "jwt-env")

        provider = openwebui(
            "gpt-4o",
            base_url="http://owui/api",
            api_key="jwt-explicit",
            http_client=_mock_client("http://owui/api"),
        )

        assert provider._api_key == "jwt-explicit"

    def test_default_features_include_vision(
        self,
        monkeypatch: pytest.MonkeyPatch,
    ) -> None:
        monkeypatch.setenv("OPENWEBUI_API_KEY", "jwt")

        provider = openwebui(
            "gpt-4o",
            base_url="http://owui/api",
            http_client=_mock_client("http://owui/api"),
        )

        assert provider.supports(ProviderFeature.STRUCTURED_OUTPUT)
        assert provider.supports(ProviderFeature.VISION)

    def test_features_override(self, monkeypatch: pytest.MonkeyPatch) -> None:
        monkeypatch.setenv("OPENWEBUI_API_KEY", "jwt")

        provider = openwebui(
            "gpt-4o",
            base_url="http://owui/api",
            features=frozenset({ProviderFeature.STRUCTURED_OUTPUT}),
            http_client=_mock_client("http://owui/api"),
        )

        assert provider.supports(ProviderFeature.STRUCTURED_OUTPUT)
        assert not provider.supports(ProviderFeature.VISION)
