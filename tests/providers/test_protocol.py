"""Tests for ``phronesis.providers.protocol``."""

from __future__ import annotations

from collections.abc import AsyncIterator, Sequence

import pytest

from phronesis.core.messages import Message
from phronesis.providers.chunks import Finish, LLMChunk, TextChunk
from phronesis.providers.protocol import LLMProvider, ProviderFeature
from phronesis.providers.types import LLMRequest, LLMResponse


class _MockProvider:
    """Minimal structural implementation of LLMProvider for tests."""

    def __init__(self, supported: set[ProviderFeature] | None = None) -> None:
        self._supported = supported or set()

    async def complete(self, request: LLMRequest) -> LLMResponse:
        return LLMResponse(text=f"echo:{request.model}", finish_reason="stop")

    async def stream(self, request: LLMRequest) -> AsyncIterator[LLMChunk]:
        yield TextChunk(text=request.model)
        yield Finish(reason="stop")

    def supports(self, feature: ProviderFeature) -> bool:
        return feature in self._supported

    def context_window_size(self) -> int:
        return 200_000

    def count_tokens(self, messages: Sequence[Message]) -> int:
        return 0


class TestProviderFeature:
    def test_known_members(self) -> None:
        assert ProviderFeature.STRUCTURED_OUTPUT.value == "structured_output"
        assert ProviderFeature.PROMPT_CACHING.value == "prompt_caching"
        assert ProviderFeature.VISION.value == "vision"
        assert ProviderFeature.DOCUMENTS.value == "documents"
        assert ProviderFeature.EXTENDED_THINKING.value == "extended_thinking"
        assert ProviderFeature.REASONING_EFFORT.value == "reasoning_effort"
        assert ProviderFeature.PREDICTED_OUTPUTS.value == "predicted_outputs"


class TestLLMProviderRuntimeCheck:
    def test_mock_satisfies_protocol(self) -> None:
        provider = _MockProvider()

        assert isinstance(provider, LLMProvider)

    def test_non_conforming_object_fails(self) -> None:
        class NotAProvider:
            pass

        assert not isinstance(NotAProvider(), LLMProvider)


class TestMockProviderBehavior:
    @pytest.mark.asyncio
    async def test_complete_returns_response(self) -> None:
        provider = _MockProvider()
        request = LLMRequest(model="m", messages=())

        response = await provider.complete(request)

        assert response.text == "echo:m"
        assert response.finish_reason == "stop"

    @pytest.mark.asyncio
    async def test_stream_yields_chunks(self) -> None:
        provider = _MockProvider()
        request = LLMRequest(model="m", messages=())

        chunks = [chunk async for chunk in provider.stream(request)]

        assert chunks == [TextChunk(text="m"), Finish(reason="stop")]

    def test_supports_reflects_constructor_set(self) -> None:
        provider = _MockProvider({ProviderFeature.VISION})

        assert provider.supports(ProviderFeature.VISION)
        assert not provider.supports(ProviderFeature.STRUCTURED_OUTPUT)
