"""Factories for OpenAI-compatible runtimes (Ollama, vLLM, OpenWebUI).

Thin wrappers around :func:`openai` that pre-fill ``base_url``, auth
and a conservative capability set per runtime. Runtime-specific knobs
(``keep_alive``, ``num_ctx``, ``guided_json``, ``min_p``, ...) are
passed by callers via :attr:`LLMRequest.extra_body`.
"""

from __future__ import annotations

import os

import httpx

from phronesis.providers.errors import AuthenticationError
from phronesis.providers.openai.factory import openai
from phronesis.providers.openai.provider import OpenAIProvider
from phronesis.providers.protocol import ProviderFeature
from phronesis.providers.retry_config import RetryConfig

_OLLAMA_DEFAULT_HOST = "http://localhost:11434"
_OLLAMA_DEFAULT_TIMEOUT = 120.0
_VLLM_DEFAULT_TIMEOUT = 60.0
_OPENWEBUI_DEFAULT_TIMEOUT = 60.0
_OPENWEBUI_API_KEY_ENV = "OPENWEBUI_API_KEY"

_OLLAMA_FEATURES: frozenset[ProviderFeature] = frozenset({ProviderFeature.STRUCTURED_OUTPUT})
_VLLM_FEATURES: frozenset[ProviderFeature] = frozenset({ProviderFeature.STRUCTURED_OUTPUT})
_OPENWEBUI_FEATURES: frozenset[ProviderFeature] = frozenset(
    {ProviderFeature.STRUCTURED_OUTPUT, ProviderFeature.VISION}
)


def ollama(
    model: str,
    *,
    host: str = _OLLAMA_DEFAULT_HOST,
    temperature: float | None = None,
    max_tokens: int | None = None,
    timeout: float = _OLLAMA_DEFAULT_TIMEOUT,
    features: frozenset[ProviderFeature] | None = None,
    context_window: int | None = None,
    retry: RetryConfig | None = None,
    http_client: httpx.AsyncClient | None = None,
) -> OpenAIProvider:
    """Build an :class:`OpenAIProvider` pointed at a local Ollama server.

    Args:
        model: Ollama model tag (e.g. ``"qwen2.5"``, ``"llama-3.1"``).
        host: Base host URL. ``/v1`` is appended automatically.
        temperature: Default sampling temperature.
        max_tokens: Default output token cap.
        timeout: HTTP timeout (defaults higher to absorb cold-start
            warm-up of local models).
        features: Capability override. ``None`` advertises only
            :attr:`ProviderFeature.STRUCTURED_OUTPUT`.
        context_window: Override for the context window size.
        retry: Retry configuration.
        http_client: Pre-built async client (caller closes it).

    Returns:
        A configured :class:`OpenAIProvider`. Runtime-specific knobs
        (``keep_alive``, ``options.num_ctx``, ...) are passed per
        request via :attr:`LLMRequest.extra_body`.
    """
    base_url = host.rstrip("/")

    return openai(
        model,
        api_key="",
        base_url=base_url,
        temperature=temperature,
        max_tokens=max_tokens,
        timeout=timeout,
        retry=retry,
        http_client=http_client,
        features=features if features is not None else _OLLAMA_FEATURES,
        context_window=context_window,
    )


def vllm(
    model: str,
    *,
    base_url: str,
    api_key: str | None = None,
    temperature: float | None = None,
    max_tokens: int | None = None,
    timeout: float = _VLLM_DEFAULT_TIMEOUT,
    features: frozenset[ProviderFeature] | None = None,
    context_window: int | None = None,
    retry: RetryConfig | None = None,
    http_client: httpx.AsyncClient | None = None,
) -> OpenAIProvider:
    """Build an :class:`OpenAIProvider` pointed at a vLLM server.

    Args:
        model: HuggingFace-style model id served by vLLM.
        base_url: vLLM endpoint base URL (e.g.
            ``"http://gpu-box:8000"``).
        api_key: Optional bearer token (only meaningful when vLLM is
            started with ``--api-key``). ``None`` sends no auth.
        temperature: Default sampling temperature.
        max_tokens: Default output token cap.
        timeout: HTTP timeout.
        features: Capability override. ``None`` advertises only
            :attr:`ProviderFeature.STRUCTURED_OUTPUT`.
        context_window: Override for the context window size.
        retry: Retry configuration.
        http_client: Pre-built async client (caller closes it).

    Returns:
        A configured :class:`OpenAIProvider`. vLLM-specific guided
        decoding (``guided_json``, ``guided_choice``, ``min_p``,
        ``repetition_penalty``) is passed via
        :attr:`LLMRequest.extra_body`.
    """
    return openai(
        model,
        api_key=api_key if api_key is not None else "",
        base_url=base_url,
        temperature=temperature,
        max_tokens=max_tokens,
        timeout=timeout,
        retry=retry,
        http_client=http_client,
        features=features if features is not None else _VLLM_FEATURES,
        context_window=context_window,
    )


def openwebui(
    model: str,
    *,
    base_url: str,
    api_key: str | None = None,
    temperature: float | None = None,
    max_tokens: int | None = None,
    timeout: float = _OPENWEBUI_DEFAULT_TIMEOUT,
    features: frozenset[ProviderFeature] | None = None,
    context_window: int | None = None,
    retry: RetryConfig | None = None,
    http_client: httpx.AsyncClient | None = None,
) -> OpenAIProvider:
    """Build an :class:`OpenAIProvider` pointed at an OpenWebUI server.

    Args:
        model: Model id exposed by OpenWebUI.
        base_url: OpenWebUI endpoint with the ``/api`` suffix
            included (e.g. ``"http://host/api"``).
        api_key: JWT issued by OpenWebUI. Falls back to the
            ``OPENWEBUI_API_KEY`` environment variable.
        temperature: Default sampling temperature.
        max_tokens: Default output token cap.
        timeout: HTTP timeout.
        features: Capability override. ``None`` advertises
            :attr:`ProviderFeature.STRUCTURED_OUTPUT` and
            :attr:`ProviderFeature.VISION` (conservative; actual
            support depends on the served model).
        context_window: Override for the context window size.
        retry: Retry configuration.
        http_client: Pre-built async client (caller closes it).

    Returns:
        A configured :class:`OpenAIProvider`.

    Raises:
        AuthenticationError: If neither ``api_key`` nor
            ``OPENWEBUI_API_KEY`` are set.
    """
    resolved_key = api_key if api_key is not None else os.environ.get(_OPENWEBUI_API_KEY_ENV)

    if not resolved_key:
        raise AuthenticationError(
            f"Missing OpenWebUI API key: pass api_key=... or set {_OPENWEBUI_API_KEY_ENV}.",
        )

    return openai(
        model,
        api_key=resolved_key,
        base_url=base_url,
        temperature=temperature,
        max_tokens=max_tokens,
        timeout=timeout,
        retry=retry,
        http_client=http_client,
        features=features if features is not None else _OPENWEBUI_FEATURES,
        context_window=context_window,
    )
