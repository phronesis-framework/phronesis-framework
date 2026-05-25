"""Anthropic provider implementation.

See ``docs/PROVIDERS-DECISIONS.md`` (D-01, D-02, D-04, D-12). This module
implements the synchronous ``complete`` path against Anthropic's
``/v1/messages`` endpoint using :mod:`httpx` directly (no SDK
dependency). Streaming will land in a later phase.
"""

from __future__ import annotations

from collections.abc import AsyncIterator
from typing import Any, ClassVar

import httpx

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
from phronesis.providers.types import LLMRequest, LLMResponse
from phronesis.providers.usage import TokenUsage

_DEFAULT_API_VERSION = "2023-06-01"
_DEFAULT_MAX_TOKENS = 4096


class AnthropicProvider:
    """Concrete Anthropic provider.

    Built via the public :func:`phronesis.providers.anthropic` factory.
    """

    _SUPPORTED_FEATURES: ClassVar[frozenset[ProviderFeature]] = frozenset(
        {
            ProviderFeature.PROMPT_CACHING,
            ProviderFeature.VISION,
            ProviderFeature.DOCUMENTS,
            ProviderFeature.EXTENDED_THINKING,
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
        return self._model

    def supports(self, feature: ProviderFeature) -> bool:
        return feature in self._SUPPORTED_FEATURES

    async def complete(self, request: LLMRequest) -> LLMResponse:
        body = self._build_body(request)
        payload = await self._post_with_retry(body)

        return self._parse_response(payload)

    def stream(self, request: LLMRequest) -> AsyncIterator[LLMChunk]:
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
