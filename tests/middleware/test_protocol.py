"""Tests for the :class:`Middleware` Protocol."""

from __future__ import annotations

from phronesis.middleware import Middleware, NextCall
from phronesis.providers.types import LLMRequest, LLMResponse


class TestProtocol:
    def test_function_satisfies_protocol(self) -> None:
        async def mw(request: LLMRequest, call_next: NextCall) -> LLMResponse:
            return await call_next(request)

        assert isinstance(mw, Middleware)

    def test_class_with_call_satisfies_protocol(self) -> None:
        class _Logger:
            async def __call__(self, request: LLMRequest, call_next: NextCall) -> LLMResponse:
                return await call_next(request)

        assert isinstance(_Logger(), Middleware)

    def test_plain_object_does_not_satisfy_protocol(self) -> None:
        assert not isinstance(object(), Middleware)
