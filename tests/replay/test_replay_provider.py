"""Tests for :class:`ReplayProvider`."""

from __future__ import annotations

from pathlib import Path

import pytest

from phronesis.core.messages import TextBlock, UserMessage
from phronesis.providers.protocol import ProviderFeature
from phronesis.providers.types import LLMRequest, LLMResponse
from phronesis.replay.cassette import write_cassette
from phronesis.replay.errors import CassetteExhaustedError, CassetteFormatError
from phronesis.replay.replay import ReplayProvider


class TestReplay:
    @pytest.mark.asyncio
    async def test_returns_responses_in_recorded_order(self, tmp_path: Path) -> None:
        cassette = tmp_path / "tape.jsonl"
        write_cassette(cassette, [LLMResponse(text="one"), LLMResponse(text="two")])

        provider = ReplayProvider(cassette)

        first = await provider.complete(LLMRequest(model="x", messages=()))
        second = await provider.complete(LLMRequest(model="x", messages=()))

        assert first.text == "one"
        assert second.text == "two"

    @pytest.mark.asyncio
    async def test_exhaustion_raises(self, tmp_path: Path) -> None:
        cassette = tmp_path / "tape.jsonl"
        write_cassette(cassette, [LLMResponse(text="only")])

        provider = ReplayProvider(cassette)

        await provider.complete(LLMRequest(model="x", messages=()))

        with pytest.raises(CassetteExhaustedError):
            await provider.complete(LLMRequest(model="x", messages=()))

    def test_missing_cassette_raises(self, tmp_path: Path) -> None:
        with pytest.raises(CassetteFormatError):
            ReplayProvider(tmp_path / "missing.jsonl")


class TestReplayCapabilities:
    def test_supports_returns_false_for_every_feature(self, tmp_path: Path) -> None:
        cassette = tmp_path / "tape.jsonl"
        write_cassette(cassette, [])

        provider = ReplayProvider(cassette)

        assert provider.supports(ProviderFeature.VISION) is False
        assert provider.supports(ProviderFeature.STRUCTURED_OUTPUT) is False

    def test_context_window_uses_constructor_value(self, tmp_path: Path) -> None:
        cassette = tmp_path / "tape.jsonl"
        write_cassette(cassette, [])

        provider = ReplayProvider(cassette, context_window=128_000)

        assert provider.context_window_size() == 128_000

    def test_count_tokens_uses_heuristic(self, tmp_path: Path) -> None:
        cassette = tmp_path / "tape.jsonl"
        write_cassette(cassette, [])

        provider = ReplayProvider(cassette)

        messages = (UserMessage(content=(TextBlock(text="abcdefgh"),)),)

        assert provider.count_tokens(messages) == 2  # 8 chars // 4

    @pytest.mark.asyncio
    async def test_count_tokens_exact_returns_none(self, tmp_path: Path) -> None:
        cassette = tmp_path / "tape.jsonl"
        write_cassette(cassette, [])

        provider = ReplayProvider(cassette)

        assert await provider.count_tokens_exact(()) is None

    @pytest.mark.asyncio
    async def test_stream_raises_on_iteration(self, tmp_path: Path) -> None:
        cassette = tmp_path / "tape.jsonl"
        write_cassette(cassette, [])

        provider = ReplayProvider(cassette)

        with pytest.raises(CassetteExhaustedError):
            async for _ in provider.stream(LLMRequest(model="x", messages=())):
                pass  # pragma: no cover


class TestRecordReplayIntegration:
    @pytest.mark.asyncio
    async def test_recording_then_replaying_yields_same_responses(self, tmp_path: Path) -> None:
        from collections.abc import AsyncIterator, Sequence

        from phronesis.providers.chunks import LLMChunk
        from phronesis.replay.recording import RecordingProvider

        class _Stub:
            def __init__(self, responses: list[LLMResponse]) -> None:
                self._responses = list(responses)

            async def complete(self, request: LLMRequest) -> LLMResponse:
                return self._responses.pop(0)

            def stream(self, request: LLMRequest) -> AsyncIterator[LLMChunk]:
                async def _empty() -> AsyncIterator[LLMChunk]:
                    return
                    yield  # pragma: no cover

                return _empty()

            def supports(self, feature: ProviderFeature) -> bool:
                return False

            def context_window_size(self) -> int:
                return 1

            def count_tokens(self, messages: Sequence[object]) -> int:
                return 0

            async def count_tokens_exact(self, messages: Sequence[object]) -> int | None:
                return None

        cassette = tmp_path / "tape.jsonl"
        original = [LLMResponse(text="a"), LLMResponse(text="b")]
        recorder = RecordingProvider(_Stub(list(original)), cassette)

        await recorder.complete(LLMRequest(model="x", messages=()))
        await recorder.complete(LLMRequest(model="x", messages=()))

        replay = ReplayProvider(cassette)
        replayed = [await replay.complete(LLMRequest(model="x", messages=())) for _ in range(2)]

        assert [r.text for r in replayed] == ["a", "b"]
