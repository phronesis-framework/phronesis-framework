"""OpenAI provider implementation.

Talks to ``/v1/chat/completions`` over :mod:`httpx` directly so the
framework does not depend on a vendor SDK.
:meth:`OpenAIProvider.complete` runs through the configured
:class:`RetryConfig`. :meth:`OpenAIProvider.stream` is not retried:
once the first byte is delivered, recovery is the caller's
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
    SystemMessage,
    TextBlock,
    ToolMessage,
    ToolResultBlock,
    ToolUseBlock,
    UserMessage,
)
from phronesis.core.messages import Message as DomainMessage
from phronesis.providers.chunks import LLMChunk
from phronesis.providers.openai.errors import translate_response_error
from phronesis.providers.openai.messages import from_openai_message, to_openai_messages
from phronesis.providers.openai.streaming import stream_openai_chat
from phronesis.providers.openai.tools import to_openai_tools
from phronesis.providers.protocol import ProviderFeature
from phronesis.providers.retry_config import RetryConfig, build_retry_decorator
from phronesis.providers.types import LLMRequest, LLMResponse, Message, ResponseFormat, Role
from phronesis.providers.usage import TokenUsage

_DEFAULT_CONTEXT_WINDOW = 128_000
_CHARS_PER_TOKEN = 4

_CONTEXT_WINDOWS: dict[str, int] = {
    "gpt-4o-mini": 128_000,
    "gpt-4o": 128_000,
    "gpt-4-turbo": 128_000,
    "gpt-4.1": 1_047_576,
    "gpt-4": 8_192,
    "gpt-3.5-turbo-16k": 16_385,
    "gpt-3.5-turbo": 16_385,
    "o1-preview": 128_000,
    "o1-mini": 128_000,
    "o1": 200_000,
    "o3-mini": 200_000,
    "o3": 200_000,
    "o4-mini": 200_000,
}

_OSS_CONTEXT_WINDOWS: dict[str, int] = {
    "qwen2.5": 32_768,
    "qwen2": 32_768,
    "qwen": 8_192,
    "llama-3.1": 128_000,
    "llama-3.2": 128_000,
    "llama-3": 8_192,
    "llama-2": 4_096,
    "mistral": 32_768,
    "mixtral": 32_768,
    "deepseek-r1": 64_000,
    "deepseek-coder": 16_384,
    "deepseek": 32_768,
    "phi-3": 128_000,
    "gemma-2": 8_192,
    "gemma": 8_192,
    "command-r": 128_000,
    "yi": 32_768,
}


class OpenAIProvider:
    """Concrete OpenAI provider.

    Built via the public :func:`phronesis.providers.openai` factory;
    the constructor is not part of the public surface and is
    documented here for framework maintainers.

    Attributes:
        model: Read-only accessor for the bound model id.
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
        features: frozenset[ProviderFeature] | None = None,
        context_window: int | None = None,
    ) -> None:
        """Bind the provider to a model and HTTP client.

        Args:
            model: Default OpenAI model id used when
                :attr:`LLMRequest.model` is empty.
            api_key: OpenAI API key sent as a Bearer token in the
                ``Authorization`` header. Empty string disables the
                header (anonymous local backends).
            http_client: Pre-built async HTTP client. The provider
                does not close it on shutdown.
            default_max_tokens: Output cap used when the request
                does not provide one. ``None`` lets the model decide.
            default_temperature: Sampling temperature used when the
                request does not provide one. ``None`` defers to the
                vendor default.
            retry_config: Retry policy applied to
                :meth:`complete`. ``None`` uses
                :class:`RetryConfig` defaults.
            features: Capability set advertised by :meth:`supports`.
                ``None`` uses :attr:`_SUPPORTED_FEATURES`.
            context_window: Override for :meth:`context_window_size`.
                ``None`` falls back to the static prefix tables.
        """
        self._model = model
        self._api_key = api_key
        self._http = http_client
        self._default_max_tokens = default_max_tokens
        self._default_temperature = default_temperature
        self._features = features if features is not None else self._SUPPORTED_FEATURES
        self._context_window_override = context_window

        decorator = build_retry_decorator(retry_config or RetryConfig())
        self._post_with_retry = decorator(self._post_chat)

    @property
    def model(self) -> str:
        """Return the default model id bound at construction time."""
        return self._model

    def supports(self, feature: ProviderFeature) -> bool:
        """Return ``True`` when this provider advertises ``feature``."""
        return feature in self._features

    def context_window_size(self) -> int:
        """Return the context window size for the bound model.

        Resolution order: explicit per-instance override, then the
        OpenAI prefix table, then the OSS prefix table (Qwen, Llama,
        Mistral, etc.), and finally the modern default
        (128_000 tokens).
        """
        if self._context_window_override is not None:
            return self._context_window_override

        for prefix, size in _CONTEXT_WINDOWS.items():
            if self._model.startswith(prefix):
                return size

        for prefix, size in _OSS_CONTEXT_WINDOWS.items():
            if self._model.startswith(prefix):
                return size

        return _DEFAULT_CONTEXT_WINDOW

    def count_tokens(self, messages: Sequence[DomainMessage]) -> int:
        """Estimate the token count of ``messages``.

        MVP heuristic: total character count divided by four. Avoids
        a dependency on ``tiktoken``; sufficient for compaction-trigger
        decisions.
        """
        total_chars = sum(_message_char_length(m) for m in messages)

        return total_chars // _CHARS_PER_TOKEN

    async def count_tokens_exact(self, messages: Sequence[DomainMessage]) -> int | None:
        """Return ``None``: OpenAI exposes no public counting endpoint.

        Exact counting would require the optional ``tiktoken`` package
        or the (paid) chat completions request itself; both are out
        of scope for the MVP. Callers should fall back to
        :meth:`count_tokens` when ``None`` is returned.
        """
        return None

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

        Streaming is not retried.

        Args:
            request: The :class:`LLMRequest` to dispatch.

        Returns:
            An async iterator yielding :data:`LLMChunk` events.
        """
        body = self._build_body(request)

        return stream_openai_chat(
            self._http,
            api_key=self._api_key,
            body=body,
        )

    async def _post_chat(self, body: dict[str, Any]) -> dict[str, Any]:
        headers: dict[str, str] = {"content-type": "application/json"}

        if self._api_key:
            headers["authorization"] = f"Bearer {self._api_key}"

        response = await self._http.post(
            "/v1/chat/completions",
            json=body,
            headers=headers,
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

        if request.response_format is not None:
            body["response_format"] = _to_openai_response_format(request.response_format)

        if request.extra_body is not None:
            body.update(request.extra_body)

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


def _to_openai_response_format(response_format: ResponseFormat) -> dict[str, Any]:
    return {
        "type": "json_schema",
        "json_schema": {
            "name": response_format.name,
            "schema": response_format.schema,
            "strict": response_format.strict,
        },
    }


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


def _message_char_length(message: DomainMessage) -> int:
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
