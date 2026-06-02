"""Shared fixtures and helpers for :mod:`tests.context`."""

from __future__ import annotations

from collections.abc import AsyncIterator, Sequence

from phronesis.core.messages import Message
from phronesis.providers.chunks import LLMChunk
from phronesis.providers.protocol import ProviderFeature
from phronesis.providers.types import LLMRequest, LLMResponse


class FakeProvider:
    """Minimal :class:`LLMProvider` for context builder tests."""

    def __init__(
        self,
        *,
        response_text: str = "summary",
        context_window: int = 200_000,
        token_estimate: int = 0,
    ) -> None:
        self._response_text = response_text
        self._context_window = context_window
        self._token_estimate = token_estimate
        self.requests: list[LLMRequest] = []

    async def complete(self, request: LLMRequest) -> LLMResponse:
        self.requests.append(request)

        return LLMResponse(text=self._response_text, finish_reason="stop")

    def stream(self, request: LLMRequest) -> AsyncIterator[LLMChunk]:
        async def _empty() -> AsyncIterator[LLMChunk]:
            return
            yield  # pragma: no cover - empty async generator

        return _empty()

    def supports(self, feature: ProviderFeature) -> bool:
        return False

    def context_window_size(self) -> int:
        return self._context_window

    def count_tokens(self, messages: Sequence[Message]) -> int:
        return self._token_estimate

    async def count_tokens_exact(self, messages: Sequence[Message]) -> int | None:
        return None


class ExplodingProvider(FakeProvider):
    """Provider whose :meth:`complete` always raises."""

    async def complete(self, request: LLMRequest) -> LLMResponse:
        raise RuntimeError("compactor boom")
