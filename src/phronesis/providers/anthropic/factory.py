"""Public factory for the Anthropic provider.

Each built-in provider is exposed as a typed factory function so the
public surface stays narrow. The factory hides
:class:`AnthropicProvider` construction details (HTTP client,
timeouts, API key resolution) behind a clean call site and
centralises the environment-variable fallback for the API key.
"""

from __future__ import annotations

import os

import httpx

from phronesis.providers.anthropic.provider import AnthropicProvider
from phronesis.providers.errors import AuthenticationError
from phronesis.providers.retry_config import RetryConfig

_DEFAULT_BASE_URL = "https://api.anthropic.com"
_DEFAULT_MAX_TOKENS = 4096
_DEFAULT_TIMEOUT = 60.0
_API_KEY_ENV = "ANTHROPIC_API_KEY"


def anthropic(
    model: str,
    *,
    api_key: str | None = None,
    base_url: str = _DEFAULT_BASE_URL,
    temperature: float | None = None,
    max_tokens: int = _DEFAULT_MAX_TOKENS,
    timeout: float = _DEFAULT_TIMEOUT,
    retry: RetryConfig | None = None,
    http_client: httpx.AsyncClient | None = None,
) -> AnthropicProvider:
    """Build an :class:`AnthropicProvider` for ``model``.

    Args:
        model: Anthropic model id (e.g. ``"claude-opus-4-7"``).
        api_key: Anthropic API key. Falls back to the
            ``ANTHROPIC_API_KEY`` environment variable when omitted.
        base_url: API base URL. Override for testing or proxies.
        temperature: Default sampling temperature; overridable per
            request via :attr:`LLMRequest.temperature`.
        max_tokens: Default maximum output tokens; overridable per
            request via :attr:`LLMRequest.max_tokens`.
        timeout: HTTP timeout in seconds applied to the auto-built
            client. Ignored when ``http_client`` is supplied.
        retry: Retry configuration. ``None`` uses the defaults from
            :class:`RetryConfig`.
        http_client: Pre-built :class:`httpx.AsyncClient`. When
            provided the caller is responsible for closing it.
            Useful for tests that inject a
            :class:`httpx.MockTransport`.

    Returns:
        A fully configured :class:`AnthropicProvider` ready to be
        passed to the agent loop.

    Raises:
        AuthenticationError: If no API key is supplied and the
            environment variable is unset.
    """
    resolved_key = api_key or os.environ.get(_API_KEY_ENV)

    if not resolved_key:
        raise AuthenticationError(
            f"Missing Anthropic API key: pass api_key=... or set {_API_KEY_ENV}.",
        )

    client = http_client or httpx.AsyncClient(base_url=base_url, timeout=timeout)

    return AnthropicProvider(
        model=model,
        api_key=resolved_key,
        http_client=client,
        default_max_tokens=max_tokens,
        default_temperature=temperature,
        retry_config=retry,
    )
