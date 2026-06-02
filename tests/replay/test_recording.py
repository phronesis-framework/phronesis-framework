"""Tests for :class:`RecordingProvider`."""

from __future__ import annotations

from collections.abc import AsyncIterator, Sequence
from pathlib import Path

import pytest

from phronesis.core.messages import Message
from phronesis.providers.chunks import LLMChunk
from phronesis.providers.protocol import ProviderFeature
from phronesis.providers.types import LLMRequest, LLMResponse, ToolCall
from phronesis.providers.usage import TokenUsage
from phronesis.replay.cassette import read_cassette
from phronesis.replay.recording import RecordingProvider


class _StubProvider:
    def __init__(self, responses: list[LLMResponse]) -> None:
        self._responses = list(responses)
        self.complete_calls = 0

    async def complete(self, request: LLMRequest) -> LLMResponse:
        self.complete_calls += 1

        return self._responses.pop(0)

    def stream(self, request: LLMRequest) -> AsyncIterator[LLMChunk]:
        async def _empty() -> AsyncIterator[LLMChunk]:
            return
            yield  # pragma: no cover

        return _empty()

    def supports(self, feature: ProviderFeature) -> bool:
        return feature is ProviderFeature.VISION

    def context_window_size(self) -> int:
        return 99_999

    def count_tokens(self, messages: Sequence[Message]) -> int:
        return 42

    async def count_tokens_exact(self, messages: Sequence[Message]) -> int | None:
        return 43


class TestRecording:
    @pytest.mark.asyncio
    async def test_complete_forwards_and_appends(self, tmp_path: Path) -> None:
        cassette = tmp_path / "tape.jsonl"
        stub = _StubProvider([LLMResponse(text="hello")])
        recorder = RecordingProvider(stub, cassette)

        response = await recorder.complete(LLMRequest(model="x", messages=()))

        assert response.text == "hello"
        assert stub.complete_calls == 1
        assert read_cassette(cassette) == [LLMResponse(text="hello")]

    @pytest.mark.asyncio
    async def test_multiple_completions_are_persisted_in_order(self, tmp_path: Path) -> None:
        cassette = tmp_path / "tape.jsonl"
        stub = _StubProvider(
            [
                LLMResponse(text="one", usage=TokenUsage(input_tokens=1)),
                LLMResponse(
                    text="two",
                    tool_calls=(ToolCall(call_id="c1", tool_name="t", arguments={}),),
                ),
            ],
        )
        recorder = RecordingProvider(stub, cassette)

        await recorder.complete(LLMRequest(model="x", messages=()))
        await recorder.complete(LLMRequest(model="x", messages=()))

        loaded = read_cassette(cassette)

        assert [r.text for r in loaded] == ["one", "two"]
        assert loaded[1].tool_calls[0].call_id == "c1"

    def test_construction_truncates_existing_cassette_by_default(self, tmp_path: Path) -> None:
        cassette = tmp_path / "tape.jsonl"
        cassette.write_text("stale\n", encoding="utf-8")
        stub = _StubProvider([])

        RecordingProvider(stub, cassette)

        assert cassette.read_text(encoding="utf-8") == ""

    def test_truncate_false_preserves_existing_content(self, tmp_path: Path) -> None:
        cassette = tmp_path / "tape.jsonl"
        cassette.write_text("kept\n", encoding="utf-8")
        stub = _StubProvider([])

        RecordingProvider(stub, cassette, truncate=False)

        assert cassette.read_text(encoding="utf-8") == "kept\n"


class TestRecordingMirroring:
    def test_supports_mirrors_inner(self, tmp_path: Path) -> None:
        stub = _StubProvider([])
        recorder = RecordingProvider(stub, tmp_path / "tape.jsonl")

        assert recorder.supports(ProviderFeature.VISION) is True
        assert recorder.supports(ProviderFeature.STRUCTURED_OUTPUT) is False

    def test_context_window_mirrors_inner(self, tmp_path: Path) -> None:
        stub = _StubProvider([])
        recorder = RecordingProvider(stub, tmp_path / "tape.jsonl")

        assert recorder.context_window_size() == 99_999

    def test_count_tokens_mirrors_inner(self, tmp_path: Path) -> None:
        stub = _StubProvider([])
        recorder = RecordingProvider(stub, tmp_path / "tape.jsonl")

        assert recorder.count_tokens(()) == 42

    @pytest.mark.asyncio
    async def test_count_tokens_exact_mirrors_inner(self, tmp_path: Path) -> None:
        stub = _StubProvider([])
        recorder = RecordingProvider(stub, tmp_path / "tape.jsonl")

        assert await recorder.count_tokens_exact(()) == 43
