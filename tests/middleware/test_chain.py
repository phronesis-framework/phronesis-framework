"""Tests for the middleware chain composition."""

from __future__ import annotations

from collections.abc import AsyncIterator, Sequence

import pytest

from phronesis.core.messages import Message
from phronesis.middleware import Middleware, NextCall, apply_middleware
from phronesis.providers.chunks import LLMChunk
from phronesis.providers.protocol import ProviderFeature
from phronesis.providers.types import LLMRequest, LLMResponse


class _StubProvider:
    def __init__(self, response: LLMResponse) -> None:
        self._response = response
        self.complete_calls: list[LLMRequest] = []

    async def complete(self, request: LLMRequest) -> LLMResponse:
        self.complete_calls.append(request)

        return self._response

    def stream(self, request: LLMRequest) -> AsyncIterator[LLMChunk]:
        async def _empty() -> AsyncIterator[LLMChunk]:
            return
            yield  # pragma: no cover

        return _empty()

    def supports(self, feature: ProviderFeature) -> bool:
        return feature is ProviderFeature.STRUCTURED_OUTPUT

    def context_window_size(self) -> int:
        return 12_345

    def count_tokens(self, messages: Sequence[Message]) -> int:
        return 7

    async def count_tokens_exact(self, messages: Sequence[Message]) -> int | None:
        return 8


class TestApplyMiddleware:
    @pytest.mark.asyncio
    async def test_no_middleware_returns_inner_response(self) -> None:
        inner = _StubProvider(LLMResponse(text="hi"))
        wrapped = apply_middleware(inner, [])

        result = await wrapped.complete(LLMRequest(model="m", messages=()))

        assert result.text == "hi"

    @pytest.mark.asyncio
    async def test_single_middleware_can_transform_response(self) -> None:
        inner = _StubProvider(LLMResponse(text="raw"))

        async def upper(request: LLMRequest, call_next: NextCall) -> LLMResponse:
            response = await call_next(request)

            return LLMResponse(
                text=response.text.upper(),
                tool_calls=response.tool_calls,
                finish_reason=response.finish_reason,
                usage=response.usage,
            )

        wrapped = apply_middleware(inner, [upper])

        result = await wrapped.complete(LLMRequest(model="m", messages=()))

        assert result.text == "RAW"

    @pytest.mark.asyncio
    async def test_middleware_can_short_circuit(self) -> None:
        inner = _StubProvider(LLMResponse(text="real"))

        async def cache(request: LLMRequest, call_next: NextCall) -> LLMResponse:
            return LLMResponse(text="cached")

        wrapped = apply_middleware(inner, [cache])

        result = await wrapped.complete(LLMRequest(model="m", messages=()))

        assert result.text == "cached"
        assert inner.complete_calls == []

    @pytest.mark.asyncio
    async def test_middleware_order_is_onion_outer_first(self) -> None:
        inner = _StubProvider(LLMResponse(text="x"))
        order: list[str] = []

        def make(label: str) -> Middleware:
            async def _mw(request: LLMRequest, call_next: NextCall) -> LLMResponse:
                order.append(f"{label}:before")
                response = await call_next(request)
                order.append(f"{label}:after")

                return response

            return _mw

        wrapped = apply_middleware(inner, [make("outer"), make("inner")])

        await wrapped.complete(LLMRequest(model="m", messages=()))

        assert order == [
            "outer:before",
            "inner:before",
            "inner:after",
            "outer:after",
        ]

    @pytest.mark.asyncio
    async def test_middleware_can_replace_request(self) -> None:
        inner = _StubProvider(LLMResponse(text=""))

        async def rewrite(request: LLMRequest, call_next: NextCall) -> LLMResponse:
            new_request = LLMRequest(model="OVERRIDDEN", messages=request.messages)

            return await call_next(new_request)

        wrapped = apply_middleware(inner, [rewrite])

        await wrapped.complete(LLMRequest(model="original", messages=()))

        assert inner.complete_calls[0].model == "OVERRIDDEN"

    def test_apply_middleware_does_not_mutate_input_list(self) -> None:
        inner = _StubProvider(LLMResponse())
        middlewares: list[Middleware] = []

        apply_middleware(inner, middlewares)

        assert middlewares == []


class TestPassthrough:
    def test_supports_passes_through(self) -> None:
        wrapped = apply_middleware(_StubProvider(LLMResponse()), [])

        assert wrapped.supports(ProviderFeature.STRUCTURED_OUTPUT) is True
        assert wrapped.supports(ProviderFeature.VISION) is False

    def test_context_window_passes_through(self) -> None:
        wrapped = apply_middleware(_StubProvider(LLMResponse()), [])

        assert wrapped.context_window_size() == 12_345

    def test_count_tokens_passes_through(self) -> None:
        wrapped = apply_middleware(_StubProvider(LLMResponse()), [])

        assert wrapped.count_tokens(()) == 7

    @pytest.mark.asyncio
    async def test_count_tokens_exact_passes_through(self) -> None:
        wrapped = apply_middleware(_StubProvider(LLMResponse()), [])

        assert await wrapped.count_tokens_exact(()) == 8

    @pytest.mark.asyncio
    async def test_stream_is_not_intercepted(self) -> None:
        called: list[int] = []

        class _Spy(_StubProvider):
            def stream(self, request: LLMRequest) -> AsyncIterator[LLMChunk]:
                called.append(1)

                return super().stream(request)

        async def short_circuit(request: LLMRequest, call_next: NextCall) -> LLMResponse:
            return LLMResponse(text="never reached")

        spy = _Spy(LLMResponse())
        wrapped = apply_middleware(spy, [short_circuit])

        async for _ in wrapped.stream(LLMRequest(model="m", messages=())):
            pass  # pragma: no cover

        assert called == [1]
