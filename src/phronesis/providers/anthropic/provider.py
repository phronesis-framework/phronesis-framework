"""Anthropic provider implementation.

Talks to Anthropic's ``/v1/messages`` endpoint over :mod:`httpx`
directly so the framework does not depend on a vendor SDK.
:meth:`AnthropicProvider.complete` runs through the configured
:class:`RetryConfig`. :meth:`AnthropicProvider.stream` is not
retried: once the first byte is delivered, recovery is the caller's
responsibility.
"""

from __future__ import annotations

from collections.abc import AsyncIterator, Sequence
from typing import Any, ClassVar

import httpx

from phronesis.core.messages import (
    AssistantMessage,
    CompactionSummaryBlock,
    ContentBlock,
    Message,
    SystemMessage,
    TextBlock,
    ToolMessage,
    ToolResultBlock,
    ToolUseBlock,
    UserMessage,
)
from phronesis.providers.anthropic.errors import translate_response_error
from phronesis.providers.anthropic.messages import (
    from_anthropic_content,
    to_anthropic_messages,
)
from phronesis.providers.anthropic.streaming import stream_anthropic_messages
from phronesis.providers.anthropic.tools import to_anthropic_tools
from phronesis.providers.chunks import LLMChunk
from phronesis.providers.protocol import ProviderFeature
from phronesis.providers.retry_config import RetryConfig, build_retry_decorator
from phronesis.providers.translation import translate_history
from phronesis.providers.types import LLMRequest, LLMResponse
from phronesis.providers.usage import TokenUsage

_DEFAULT_API_VERSION = "2023-06-01"
_DEFAULT_MAX_TOKENS = 4096
_DEFAULT_CONTEXT_WINDOW = 200_000
_CHARS_PER_TOKEN = 4

_CONTEXT_WINDOWS: dict[str, int] = {
    "claude-3-5-sonnet": 200_000,
    "claude-3-5-haiku": 200_000,
    "claude-3-7-sonnet": 200_000,
    "claude-3-opus": 200_000,
    "claude-3-sonnet": 200_000,
    "claude-3-haiku": 200_000,
    "claude-opus-4": 200_000,
    "claude-sonnet-4": 200_000,
    "claude-haiku-4": 200_000,
}


class AnthropicProvider:
    """Concrete Anthropic provider.

    Built via the public :func:`phronesis.providers.anthropic`
    factory; the constructor is not part of the public surface and
    is documented here for framework maintainers.

    Attributes:
        model: Read-only accessor for the bound model id.
    """

    _SUPPORTED_FEATURES: ClassVar[frozenset[ProviderFeature]] = frozenset(
        {
            ProviderFeature.PROMPT_CACHING,
            ProviderFeature.VISION,
            ProviderFeature.DOCUMENTS,
            ProviderFeature.EXTENDED_THINKING,
            ProviderFeature.NATIVE_TOKEN_COUNT,
        }
    )

    def __init__(
        self,
        *,
        model: str,
        api_key: str,
        http_client: httpx.AsyncClient,
        api_version: str = _DEFAULT_API_VERSION,
        default_max_tokens: int = _DEFAULT_MAX_TOKENS,
        default_temperature: float | None = None,
        retry_config: RetryConfig | None = None,
    ) -> None:
        """Bind the provider to a model and HTTP client.

        Args:
            model: Default Anthropic model id used when
                :attr:`LLMRequest.model` is empty.
            api_key: Anthropic API key sent in the ``x-api-key``
                header.
            http_client: Pre-built async HTTP client. The provider
                does not close it on shutdown.
            api_version: Value of the ``anthropic-version`` header.
            default_max_tokens: Output cap used when the request
                does not provide one.
            default_temperature: Sampling temperature used when the
                request does not provide one. ``None`` defers to the
                vendor default.
            retry_config: Retry policy applied to
                :meth:`complete`. ``None`` uses
                :class:`RetryConfig` defaults.
        """
        self._model = model
        self._api_key = api_key
        self._http = http_client
        self._api_version = api_version
        self._default_max_tokens = default_max_tokens
        self._default_temperature = default_temperature

        decorator = build_retry_decorator(retry_config or RetryConfig())
        self._post_with_retry = decorator(self._post_messages)

    @property
    def model(self) -> str:
        """Return the default model id bound at construction time."""
        return self._model

    def supports(self, feature: ProviderFeature) -> bool:
        """Return ``True`` when this provider advertises ``feature``."""
        return feature in self._SUPPORTED_FEATURES

    def context_window_size(self) -> int:
        """Return the context window size for the bound Anthropic model.

        Looked up in a static table keyed by the model prefix; unknown
        models fall back to the family default (200_000 tokens).
        """
        for prefix, size in _CONTEXT_WINDOWS.items():
            if self._model.startswith(prefix):
                return size

        return _DEFAULT_CONTEXT_WINDOW

    def count_tokens(self, messages: Sequence[Message]) -> int:
        """Estimate the token count of ``messages``.

        MVP heuristic: total character count divided by four. Avoids
        a network round-trip and any vendor SDK dependency; precise
        enough for compaction-trigger decisions.
        """
        total_chars = sum(_message_char_length(m) for m in messages)

        return total_chars // _CHARS_PER_TOKEN

    async def count_tokens_exact(self, messages: Sequence[Message]) -> int | None:
        """Return the exact token count via Anthropic's counting endpoint.

        Calls ``POST /v1/messages/count_tokens`` with the translated
        request body. The endpoint is unmetered but still a network
        round-trip; callers should reserve it for decisions that
        warrant the latency (precise budgeting, hard limits) and
        keep :meth:`count_tokens` for hot-path scheduling.

        Returns:
            Exact token count, or ``None`` if the endpoint response
            is malformed (defensive - the heuristic is a safe
            fallback).
        """
        provider_messages = translate_history(messages)
        translated_messages, system = to_anthropic_messages(provider_messages)
        body: dict[str, Any] = {
            "model": self._model,
            "messages": translated_messages,
        }

        if system:
            body["system"] = system

        response = await self._http.post(
            "/v1/messages/count_tokens",
            json=body,
            headers={
                "x-api-key": self._api_key,
                "anthropic-version": self._api_version,
                "content-type": "application/json",
            },
        )

        if response.status_code >= 400:
            raise translate_response_error(response)

        data = response.json()

        if not isinstance(data, dict):
            return None

        raw = data.get("input_tokens")

        return raw if isinstance(raw, int) else None

    async def complete(self, request: LLMRequest) -> LLMResponse:
        """Send ``request`` and await the full response.

        The HTTP call is wrapped by the retry decorator built from
        the provider's :class:`RetryConfig`, so transient transport,
        server and rate-limit failures are re-tried transparently.

        Args:
            request: The :class:`LLMRequest` to dispatch.

        Returns:
            The parsed :class:`LLMResponse`.
        """
        body = self._build_body(request)
        payload = await self._post_with_retry(body)

        return self._parse_response(payload)

    def stream(self, request: LLMRequest) -> AsyncIterator[LLMChunk]:
        """Stream ``request`` chunk-by-chunk.

        Streaming is not retried: once the first byte is delivered,
        recovery is the caller's responsibility.

        Args:
            request: The :class:`LLMRequest` to dispatch.

        Returns:
            An async iterator yielding :data:`LLMChunk` events.
        """
        body = self._build_body(request)

        return stream_anthropic_messages(
            self._http,
            api_key=self._api_key,
            api_version=self._api_version,
            body=body,
        )

    async def _post_messages(self, body: dict[str, Any]) -> dict[str, Any]:
        response = await self._http.post(
            "/v1/messages",
            json=body,
            headers={
                "x-api-key": self._api_key,
                "anthropic-version": self._api_version,
                "content-type": "application/json",
            },
        )

        if response.status_code >= 400:
            raise translate_response_error(response)

        data = response.json()

        if not isinstance(data, dict):
            return {}

        return data

    def _build_body(self, request: LLMRequest) -> dict[str, Any]:
        messages, system_from_messages = to_anthropic_messages(request.messages)
        model = request.model or self._model
        max_tokens = (
            request.max_tokens if request.max_tokens is not None else self._default_max_tokens
        )

        body: dict[str, Any] = {
            "model": model,
            "max_tokens": max_tokens,
            "messages": messages,
        }
        system = request.system or system_from_messages

        if system:
            body["system"] = system

        temperature = (
            request.temperature if request.temperature is not None else self._default_temperature
        )

        if temperature is not None:
            body["temperature"] = temperature

        if request.tools:
            body["tools"] = to_anthropic_tools(request.tools)

        if request.extra_body is not None:
            body.update(request.extra_body)

        return body

    def _parse_response(self, payload: dict[str, Any]) -> LLMResponse:
        raw_content = payload.get("content")
        blocks = raw_content if isinstance(raw_content, list) else []
        text, tool_calls = from_anthropic_content(blocks)
        usage = _parse_usage(payload.get("usage"))
        stop_reason = payload.get("stop_reason")

        return LLMResponse(
            text=text,
            tool_calls=tool_calls,
            finish_reason=str(stop_reason) if stop_reason else "",
            usage=usage,
        )


def _parse_usage(raw: Any) -> TokenUsage | None:
    if not isinstance(raw, dict):
        return None

    return TokenUsage(
        input_tokens=_opt_int(raw.get("input_tokens")),
        output_tokens=_opt_int(raw.get("output_tokens")),
        cache_read_tokens=_opt_int(raw.get("cache_read_input_tokens")),
        cache_creation_tokens=_opt_int(raw.get("cache_creation_input_tokens")),
    )


def _opt_int(value: Any) -> int | None:
    return value if isinstance(value, int) else None


def _message_char_length(message: Message) -> int:
    if isinstance(message, SystemMessage | UserMessage | AssistantMessage | ToolMessage):
        return sum(_block_char_length(b) for b in message.content)

    return 0


def _block_char_length(block: ContentBlock) -> int:
    if isinstance(block, TextBlock):
        return len(block.text)

    if isinstance(block, CompactionSummaryBlock):
        return len(block.text)

    if isinstance(block, ToolUseBlock):
        return len(block.tool_name) + sum(len(str(v)) for v in block.args.values())

    if isinstance(block, ToolResultBlock):
        return len(str(block.output))

    return 0
