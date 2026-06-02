"""Shared fixtures for agent tests."""

from __future__ import annotations

from collections.abc import AsyncIterator, Sequence
from typing import Any

import pytest

from phronesis.core.messages import Message
from phronesis.providers.chunks import LLMChunk
from phronesis.providers.protocol import LLMProvider, ProviderFeature
from phronesis.providers.types import LLMRequest, LLMResponse
from phronesis.tools.decorator import tool
from phronesis.tools.tool import Tool


class _FakeProvider:
    """Minimal :class:`LLMProvider` that returns canned responses."""

    def __init__(self, response: LLMResponse | None = None) -> None:
        self._response = response or LLMResponse(text="done", finish_reason="stop")

    async def complete(self, request: LLMRequest) -> LLMResponse:
        return self._response

    def stream(self, request: LLMRequest) -> AsyncIterator[LLMChunk]:
        async def _empty() -> AsyncIterator[LLMChunk]:
            return
            yield  # pragma: no cover - empty async generator

        return _empty()

    def supports(self, feature: ProviderFeature) -> bool:
        return False

    def context_window_size(self) -> int:
        return 200_000

    def count_tokens(self, messages: Sequence[Message]) -> int:
        return 0

    async def count_tokens_exact(self, messages: Sequence[Message]) -> int | None:
        return None


@pytest.fixture
def provider() -> LLMProvider:
    return _FakeProvider()


@tool(name="alpha")
def _alpha(query: str) -> dict[str, Any]:
    return {"query": query}


@tool(name="beta")
def _beta(payload: dict[str, Any]) -> dict[str, Any]:
    return payload


@pytest.fixture
def tool_a() -> Tool:
    return _alpha


@pytest.fixture
def tool_b() -> Tool:
    return _beta
