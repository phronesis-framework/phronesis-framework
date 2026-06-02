"""Public factory for the OpenAI provider.

Mirrors the Anthropic factory in shape: hides
:class:`OpenAIProvider` construction details (HTTP client,
timeouts, API key resolution) behind a clean call site and centralises
the environment-variable fallback for the API key.
"""

from __future__ import annotations

import os

import httpx

from phronesis.providers.errors import AuthenticationError
from phronesis.providers.openai.provider import OpenAIProvider
from phronesis.providers.protocol import ProviderFeature
from phronesis.providers.retry_config import RetryConfig

_DEFAULT_BASE_URL = "https://api.openai.com"
_DEFAULT_TIMEOUT = 60.0
_API_KEY_ENV = "OPENAI_API_KEY"


def openai(
    model: str,
    *,
    api_key: str | None = None,
    base_url: str = _DEFAULT_BASE_URL,
    temperature: float | None = None,
    max_tokens: int | None = None,
    timeout: float = _DEFAULT_TIMEOUT,
    retry: RetryConfig | None = None,
    http_client: httpx.AsyncClient | None = None,
    features: frozenset[ProviderFeature] | None = None,
    context_window: int | None = None,
) -> OpenAIProvider:
    """Build an :class:`OpenAIProvider` for ``model``.

    Args:
        model: OpenAI model id (e.g. ``"gpt-4o"``).
        api_key: OpenAI API key. Falls back to the ``OPENAI_API_KEY``
            environment variable when omitted.
        base_url: API base URL. Override for testing or proxies.
        temperature: Default sampling temperature; overridable per
            request via :attr:`LLMRequest.temperature`.
        max_tokens: Default maximum output tokens; ``None`` lets the
            model decide. Overridable per request via
            :attr:`LLMRequest.max_tokens`.
        timeout: HTTP timeout in seconds applied to the auto-built
            client. Ignored when ``http_client`` is supplied.
        retry: Retry configuration. ``None`` uses the defaults from
            :class:`RetryConfig`.
        http_client: Pre-built :class:`httpx.AsyncClient`. When
            provided the caller is responsible for closing it.
            Useful for tests that inject a
            :class:`httpx.MockTransport`.
        features: Capability set advertised by
            :meth:`OpenAIProvider.supports`. ``None`` uses the
            built-in OpenAI defaults. OSS factories pass a narrower
            set.
        context_window: Override for
            :meth:`OpenAIProvider.context_window_size`. ``None``
            falls back to the static prefix tables.

    Returns:
        A fully configured :class:`OpenAIProvider` ready to be
        passed to the agent loop.

    Raises:
        AuthenticationError: If no API key is supplied, the
            environment variable is unset, and ``base_url`` points
            at the public OpenAI endpoint. When ``base_url`` is
            custom (OSS backends), an empty key is accepted and the
            ``Authorization`` header is omitted.
    """
    resolved_key = api_key if api_key is not None else os.environ.get(_API_KEY_ENV)

    if not resolved_key:
        if base_url == _DEFAULT_BASE_URL:
            raise AuthenticationError(
                f"Missing OpenAI API key: pass api_key=... or set {_API_KEY_ENV}.",
            )

        resolved_key = ""

    client = http_client or httpx.AsyncClient(base_url=base_url, timeout=timeout)

    return OpenAIProvider(
        model=model,
        api_key=resolved_key,
        http_client=client,
        default_max_tokens=max_tokens,
        default_temperature=temperature,
        retry_config=retry,
        features=features,
        context_window=context_window,
    )
