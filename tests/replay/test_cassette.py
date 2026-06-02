"""Tests for the JSONL cassette format."""

from __future__ import annotations

from pathlib import Path

import pytest

from phronesis.providers.types import LLMResponse, ToolCall
from phronesis.providers.usage import TokenUsage
from phronesis.replay.cassette import (
    append_cassette,
    decode_response,
    encode_response,
    read_cassette,
    write_cassette,
)
from phronesis.replay.errors import CassetteFormatError


class TestEncodeDecodeResponse:
    def test_round_trip_minimal_response(self) -> None:
        original = LLMResponse(text="hi")

        payload = encode_response(original)
        decoded = decode_response(payload)

        assert decoded == original

    def test_round_trip_with_tool_calls_and_usage(self) -> None:
        original = LLMResponse(
            text="thinking",
            tool_calls=(ToolCall(call_id="c1", tool_name="search", arguments={"q": "weather"}),),
            finish_reason="tool_use",
            usage=TokenUsage(input_tokens=10, output_tokens=5),
        )

        decoded = decode_response(encode_response(original))

        assert decoded.text == original.text
        assert decoded.tool_calls == original.tool_calls
        assert decoded.finish_reason == original.finish_reason
        assert decoded.usage == original.usage

    def test_decode_malformed_payload_raises(self) -> None:
        with pytest.raises(CassetteFormatError):
            decode_response({"tool_calls": [{"missing": "fields"}]})


class TestCassetteRoundTrip:
    def test_write_and_read_round_trips(self, tmp_path: Path) -> None:
        cassette = tmp_path / "tape.jsonl"
        responses = [
            LLMResponse(text="one"),
            LLMResponse(text="two", usage=TokenUsage(input_tokens=3)),
        ]

        write_cassette(cassette, responses)
        loaded = read_cassette(cassette)

        assert loaded == responses

    def test_append_preserves_existing_entries(self, tmp_path: Path) -> None:
        cassette = tmp_path / "tape.jsonl"
        write_cassette(cassette, [LLMResponse(text="first")])

        append_cassette(cassette, LLMResponse(text="second"))

        loaded = read_cassette(cassette)

        assert [r.text for r in loaded] == ["first", "second"]

    def test_blank_lines_are_skipped(self, tmp_path: Path) -> None:
        cassette = tmp_path / "tape.jsonl"
        cassette.write_text(
            '{"text": "a", "tool_calls": [], "finish_reason": "", "usage": null}\n'
            "\n"
            '{"text": "b", "tool_calls": [], "finish_reason": "", "usage": null}\n',
            encoding="utf-8",
        )

        loaded = read_cassette(cassette)

        assert [r.text for r in loaded] == ["a", "b"]


class TestCassetteFormatErrors:
    def test_missing_file_raises(self, tmp_path: Path) -> None:
        with pytest.raises(CassetteFormatError) as exc:
            read_cassette(tmp_path / "missing.jsonl")

        assert "not found" in str(exc.value)

    def test_invalid_json_raises(self, tmp_path: Path) -> None:
        cassette = tmp_path / "bad.jsonl"
        cassette.write_text("{not json}\n", encoding="utf-8")

        with pytest.raises(CassetteFormatError):
            read_cassette(cassette)

    def test_non_object_line_raises(self, tmp_path: Path) -> None:
        cassette = tmp_path / "bad.jsonl"
        cassette.write_text("[1, 2, 3]\n", encoding="utf-8")

        with pytest.raises(CassetteFormatError):
            read_cassette(cassette)
