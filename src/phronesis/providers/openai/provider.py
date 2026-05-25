"""OpenAI provider implementation.

See ``docs/PROVIDERS-DECISIONS.md`` (D-01, D-02, D-04, D-12). Implements
the synchronous ``complete`` path against ``/v1/chat/completions`` using
:mod:`httpx` directly (no SDK dependency). Streaming lives in
:mod:`phronesis.providers.openai.streaming`.
"""

from __future__ import annotations

from collections.abc import AsyncIterator
from typing import Any, ClassVar

import httpx

from phronesis.providers.chunks import LLMChunk
from phronesis.providers.openai.errors import translate_response_error
from phronesis.providers.openai.messages import from_openai_message, to_openai_messages
from phronesis.providers.openai.streaming import stream_openai_chat
from phronesis.providers.openai.tools import to_openai_tools
from phronesis.providers.protocol import ProviderFeature
from phronesis.providers.retry_config import RetryConfig, build_retry_decorator
from phronesis.providers.types import LLMRequest, LLMResponse, Message, Role
from phronesis.providers.usage import TokenUsage


class OpenAIProvider:
    """Concrete OpenAI provider.

    Built via the public :func:`phronesis.providers.openai` factory.
    """

    _SUPPORTED_FEATURES: ClassVar[frozenset[ProviderFeature]] = frozenset(
        {
            ProviderFeature.STRUCTURED_OUTPUT,
            ProviderFeature.REASONING_EFFORT,
            ProviderFeature.PREDICTED_OUTPUTS,
            ProviderFeature.PROMPT_CACHING,
            ProviderFeature.VISION,
        }
    )

    def __init__(
        self,
        *,
        model: str,
        api_key: str,
        http_client: httpx.AsyncClient,
        default_max_tokens: int | None = None,
        default_temperature: float | None = None,
        retry_config: RetryConfig | None = None,
    ) -> None:
        self._model = model
        self._api_key = api_key
        self._http = http_client
        self._default_max_tokens = default_max_tokens
        self._default_temperature = default_temperature

        decorator = build_retry_decorator(retry_config or RetryConfig())
        self._post_with_retry = decorator(self._post_chat)

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

        return stream_openai_chat(
            self._http,
            api_key=self._api_key,
            body=body,
        )

    async def _post_chat(self, body: dict[str, Any]) -> dict[str, Any]:
        response = await self._http.post(
            "/v1/chat/completions",
            json=body,
            headers={
                "authorization": f"Bearer {self._api_key}",
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
        messages = self._compose_messages(request)
        model = request.model or self._model

        body: dict[str, Any] = {
            "model": model,
            "messages": to_openai_messages(messages),
        }
        max_tokens = (
            request.max_tokens if request.max_tokens is not None else self._default_max_tokens
        )

        if max_tokens is not None:
            body["max_tokens"] = max_tokens

        temperature = (
            request.temperature if request.temperature is not None else self._default_temperature
        )

        if temperature is not None:
            body["temperature"] = temperature

        if request.tools:
            body["tools"] = to_openai_tools(request.tools)

        return body

    @staticmethod
    def _compose_messages(request: LLMRequest) -> list[Message]:
        if request.system is None:
            return list(request.messages)

        prepended = Message(role=Role.SYSTEM, content=request.system)
        without_system = [m for m in request.messages if m.role is not Role.SYSTEM]

        return [prepended, *without_system]

    def _parse_response(self, payload: dict[str, Any]) -> LLMResponse:
        choices = payload.get("choices")
        first = choices[0] if isinstance(choices, list) and choices else {}
        message = first.get("message") if isinstance(first, dict) else None
        message_dict = message if isinstance(message, dict) else {}
        text, tool_calls = from_openai_message(message_dict)
        finish_reason = first.get("finish_reason") if isinstance(first, dict) else None
        usage = _parse_usage(payload.get("usage"))

        return LLMResponse(
            text=text,
            tool_calls=tool_calls,
            finish_reason=str(finish_reason) if finish_reason else "",
            usage=usage,
        )


def _parse_usage(raw: Any) -> TokenUsage | None:
    if not isinstance(raw, dict):
        return None

    prompt_details = raw.get("prompt_tokens_details")
    cache_read = prompt_details.get("cached_tokens") if isinstance(prompt_details, dict) else None

    return TokenUsage(
        input_tokens=_opt_int(raw.get("prompt_tokens")),
        output_tokens=_opt_int(raw.get("completion_tokens")),
        cache_read_tokens=_opt_int(cache_read),
        cache_creation_tokens=None,
    )


def _opt_int(value: Any) -> int | None:
    return value if isinstance(value, int) else None
