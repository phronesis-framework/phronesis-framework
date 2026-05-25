"""Public factory for the OpenAI provider.

See ``docs/PROVIDERS-DECISIONS.md`` (D-01, D-03). Mirrors the Anthropic
factory: hides :class:`OpenAIProvider` construction details (HTTP client,
timeouts, API key resolution) behind a clean call site.
"""

from __future__ import annotations

import os

import httpx

from phronesis.providers.errors import AuthenticationError
from phronesis.providers.openai.provider import OpenAIProvider
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
) -> OpenAIProvider:
    """Build an :class:`OpenAIProvider` for ``model``.

    Args:
        model: OpenAI model id (e.g. ``"gpt-4o"``).
        api_key: OpenAI API key. Falls back to the ``OPENAI_API_KEY``
            environment variable.
        base_url: API base URL. Override for testing or proxies.
        temperature: Default sampling temperature; overridable per request.
        max_tokens: Default max tokens; ``None`` lets the model decide.
        timeout: HTTP timeout in seconds. Ignored when ``http_client`` is
            provided.
        retry: Retry configuration. ``None`` uses sensible defaults.
        http_client: Pre-built :class:`httpx.AsyncClient`. When provided
            the caller is responsible for closing it. Useful for tests
            that inject a :class:`httpx.MockTransport`.

    Raises:
        AuthenticationError: If no API key is supplied and the
            environment variable is unset.
    """
    resolved_key = api_key or os.environ.get(_API_KEY_ENV)

    if not resolved_key:
        raise AuthenticationError(
            f"Missing OpenAI API key: pass api_key=... or set {_API_KEY_ENV}.",
        )

    client = http_client or httpx.AsyncClient(base_url=base_url, timeout=timeout)

    return OpenAIProvider(
        model=model,
        api_key=resolved_key,
        http_client=client,
        default_max_tokens=max_tokens,
        default_temperature=temperature,
        retry_config=retry,
    )
