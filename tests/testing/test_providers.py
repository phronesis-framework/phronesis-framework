"""Tests for the public :mod:`phronesis.testing` providers."""

from __future__ import annotations

import pytest

from phronesis.providers.protocol import LLMProvider, ProviderFeature
from phronesis.providers.types import LLMRequest, LLMResponse
from phronesis.testing import FakeProvider, ScriptedProvider


def _req() -> LLMRequest:
    return LLMRequest(model="x", messages=())


class TestFakeProviderProtocol:
    def test_satisfies_protocol(self) -> None:
        provider: LLMProvider = FakeProvider()

        assert provider is not None

    def test_default_response_has_done_text(self) -> None:
        provider = FakeProvider()

        assert provider.response.text == "done"
        assert provider.response.finish_reason == "stop"

    def test_custom_response_kept(self) -> None:
        resp = LLMResponse(text="hello", finish_reason="stop")

        provider = FakeProvider(resp)

        assert provider.response is resp


class TestFakeProviderComplete:
    @pytest.mark.asyncio
    async def test_returns_canned_response(self) -> None:
        resp = LLMResponse(text="hi", finish_reason="stop")
        provider = FakeProvider(resp)

        got = await provider.complete(_req())

        assert got is resp

    @pytest.mark.asyncio
    async def test_records_each_call(self) -> None:
        provider = FakeProvider()
        request = _req()

        await provider.complete(request)
        await provider.complete(request)

        assert provider.calls == (request, request)


class TestFakeProviderFeatures:
    def test_supports_returns_false(self) -> None:
        provider = FakeProvider()

        for feature in ProviderFeature:
            assert provider.supports(feature) is False

    def test_default_context_window(self) -> None:
        assert FakeProvider().context_window_size() == 200_000

    def test_custom_context_window(self) -> None:
        assert FakeProvider(context_window=8_000).context_window_size() == 8_000

    def test_count_tokens_is_zero(self) -> None:
        assert FakeProvider().count_tokens(()) == 0


class TestScriptedProviderComplete:
    @pytest.mark.asyncio
    async def test_returns_responses_in_order(self) -> None:
        a = LLMResponse(text="a", finish_reason="stop")
        b = LLMResponse(text="b", finish_reason="stop")
        provider = ScriptedProvider([a, b])

        first = await provider.complete(_req())
        second = await provider.complete(_req())

        assert first is a
        assert second is b

    @pytest.mark.asyncio
    async def test_remaining_decrements(self) -> None:
        provider = ScriptedProvider([LLMResponse(text="a"), LLMResponse(text="b")])

        assert provider.remaining == 2

        await provider.complete(_req())

        assert provider.remaining == 1

    @pytest.mark.asyncio
    async def test_raises_when_exhausted(self) -> None:
        provider = ScriptedProvider([LLMResponse(text="a")])
        await provider.complete(_req())

        with pytest.raises(IndexError, match="exhausted"):
            await provider.complete(_req())

    @pytest.mark.asyncio
    async def test_records_calls(self) -> None:
        provider = ScriptedProvider([LLMResponse(text="a"), LLMResponse(text="b")])

        await provider.complete(_req())
        await provider.complete(_req())

        assert len(provider.calls) == 2


class TestScriptedProviderProtocol:
    def test_satisfies_protocol(self) -> None:
        provider: LLMProvider = ScriptedProvider([LLMResponse(text="a")])

        assert provider is not None

    def test_supports_returns_false(self) -> None:
        provider = ScriptedProvider([LLMResponse(text="a")])

        for feature in ProviderFeature:
            assert provider.supports(feature) is False

    def test_count_tokens_is_zero(self) -> None:
        provider = ScriptedProvider([LLMResponse(text="a")])

        assert provider.count_tokens(()) == 0
