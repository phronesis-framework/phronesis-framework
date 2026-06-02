"""Tests for :class:`FallbackProvider`."""

from __future__ import annotations

from collections.abc import AsyncIterator, Sequence

import pytest

from phronesis.core.messages import Message
from phronesis.providers.chunks import Finish, LLMChunk, TextChunk
from phronesis.providers.errors import ProviderError, RateLimitError
from phronesis.providers.fallback import FallbackExhaustedError, FallbackProvider
from phronesis.providers.protocol import LLMProvider, ProviderFeature
from phronesis.providers.types import LLMRequest, LLMResponse


class _StubProvider:
    """Configurable provider double for fallback tests."""

    def __init__(
        self,
        *,
        complete_response: LLMResponse | None = None,
        complete_error: BaseException | None = None,
        chunks: Sequence[LLMChunk] = (),
        stream_error: BaseException | None = None,
        supports_value: bool = False,
        context_window: int = 1234,
        token_count: int = 7,
        exact_token_count: int | None = 8,
    ) -> None:
        self.complete_response = complete_response
        self.complete_error = complete_error
        self.chunks = list(chunks)
        self.stream_error = stream_error
        self.supports_value = supports_value
        self.context_window = context_window
        self.token_count = token_count
        self.exact_token_count = exact_token_count
        self.complete_calls: list[LLMRequest] = []
        self.stream_calls: list[LLMRequest] = []

    async def complete(self, request: LLMRequest) -> LLMResponse:
        self.complete_calls.append(request)

        if self.complete_error is not None:
            raise self.complete_error

        assert self.complete_response is not None

        return self.complete_response

    def stream(self, request: LLMRequest) -> AsyncIterator[LLMChunk]:
        self.stream_calls.append(request)
        chunks = list(self.chunks)
        error = self.stream_error

        async def _gen() -> AsyncIterator[LLMChunk]:
            if error is not None:
                raise error

            for chunk in chunks:
                yield chunk

        return _gen()

    def supports(self, feature: ProviderFeature) -> bool:
        return self.supports_value

    def context_window_size(self) -> int:
        return self.context_window

    def count_tokens(self, messages: Sequence[Message]) -> int:
        return self.token_count

    async def count_tokens_exact(self, messages: Sequence[Message]) -> int | None:
        return self.exact_token_count


class TestConstruction:
    def test_empty_provider_list_is_rejected(self) -> None:
        with pytest.raises(ValueError, match="at least one"):
            FallbackProvider([])

    def test_wrapper_is_an_llm_provider(self) -> None:
        wrapper = FallbackProvider([_StubProvider(complete_response=LLMResponse())])

        assert isinstance(wrapper, LLMProvider)


class TestCompleteFallback:
    @pytest.mark.asyncio
    async def test_first_provider_success_is_returned(self) -> None:
        first = _StubProvider(complete_response=LLMResponse(text="hi"))
        second = _StubProvider(complete_response=LLMResponse(text="ignored"))

        wrapper = FallbackProvider([first, second])

        result = await wrapper.complete(LLMRequest(model="m", messages=()))

        assert result.text == "hi"
        assert len(first.complete_calls) == 1
        assert second.complete_calls == []

    @pytest.mark.asyncio
    async def test_falls_back_to_next_on_provider_error(self) -> None:
        first = _StubProvider(complete_error=RateLimitError("429"))
        second = _StubProvider(complete_response=LLMResponse(text="ok"))

        wrapper = FallbackProvider([first, second])

        result = await wrapper.complete(LLMRequest(model="m", messages=()))

        assert result.text == "ok"
        assert len(first.complete_calls) == 1
        assert len(second.complete_calls) == 1

    @pytest.mark.asyncio
    async def test_raises_fallback_exhausted_when_all_fail(self) -> None:
        first = _StubProvider(complete_error=RateLimitError("first"))
        second = _StubProvider(complete_error=ProviderError("second"))

        wrapper = FallbackProvider([first, second])

        with pytest.raises(FallbackExhaustedError) as exc_info:
            await wrapper.complete(LLMRequest(model="m", messages=()))

        assert isinstance(exc_info.value.__cause__, ProviderError)
        assert str(exc_info.value.__cause__) == "second"

    @pytest.mark.asyncio
    async def test_non_fallback_exception_propagates_without_fallback(self) -> None:
        first = _StubProvider(complete_error=RuntimeError("boom"))
        second = _StubProvider(complete_response=LLMResponse(text="never"))

        wrapper = FallbackProvider([first, second])

        with pytest.raises(RuntimeError):
            await wrapper.complete(LLMRequest(model="m", messages=()))

        assert second.complete_calls == []

    @pytest.mark.asyncio
    async def test_custom_fallback_on_classes(self) -> None:
        first = _StubProvider(complete_error=RuntimeError("transient"))
        second = _StubProvider(complete_response=LLMResponse(text="ok"))

        wrapper = FallbackProvider([first, second], fallback_on=(RuntimeError,))

        result = await wrapper.complete(LLMRequest(model="m", messages=()))

        assert result.text == "ok"


class TestStreamFallback:
    @pytest.mark.asyncio
    async def test_streams_from_first_provider_on_success(self) -> None:
        first = _StubProvider(
            chunks=[TextChunk(text="a"), Finish(reason="end")],
        )
        second = _StubProvider(chunks=[TextChunk(text="ignored")])

        wrapper = FallbackProvider([first, second])
        chunks: list[LLMChunk] = []

        async for chunk in wrapper.stream(LLMRequest(model="m", messages=())):
            chunks.append(chunk)

        assert len(chunks) == 2
        assert second.stream_calls == []

    @pytest.mark.asyncio
    async def test_falls_back_when_first_stream_raises(self) -> None:
        first = _StubProvider(stream_error=RateLimitError("429"))
        second = _StubProvider(chunks=[TextChunk(text="ok")])

        wrapper = FallbackProvider([first, second])
        chunks: list[LLMChunk] = []

        async for chunk in wrapper.stream(LLMRequest(model="m", messages=())):
            chunks.append(chunk)

        assert next(c for c in chunks if isinstance(c, TextChunk)).text == "ok"
        assert len(second.stream_calls) == 1

    @pytest.mark.asyncio
    async def test_stream_exhausted_raises_fallback_exhausted(self) -> None:
        first = _StubProvider(stream_error=RateLimitError("a"))
        second = _StubProvider(stream_error=ProviderError("b"))

        wrapper = FallbackProvider([first, second])

        with pytest.raises(FallbackExhaustedError):
            async for _ in wrapper.stream(LLMRequest(model="m", messages=())):
                pass  # pragma: no cover


class TestCapabilityPassthrough:
    def test_supports_uses_first_provider(self) -> None:
        first = _StubProvider(supports_value=True)
        second = _StubProvider(supports_value=False)

        wrapper = FallbackProvider([first, second])

        assert wrapper.supports(ProviderFeature.STRUCTURED_OUTPUT) is True

    def test_context_window_uses_first_provider(self) -> None:
        first = _StubProvider(context_window=200_000)
        second = _StubProvider(context_window=8_000)

        wrapper = FallbackProvider([first, second])

        assert wrapper.context_window_size() == 200_000

    def test_count_tokens_uses_first_provider(self) -> None:
        first = _StubProvider(token_count=42)
        second = _StubProvider(token_count=99)

        wrapper = FallbackProvider([first, second])

        assert wrapper.count_tokens(()) == 42

    @pytest.mark.asyncio
    async def test_count_tokens_exact_uses_first_provider(self) -> None:
        first = _StubProvider(exact_token_count=11)
        second = _StubProvider(exact_token_count=22)

        wrapper = FallbackProvider([first, second])

        assert await wrapper.count_tokens_exact(()) == 11
