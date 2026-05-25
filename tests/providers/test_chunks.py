"""Tests for ``phronesis.providers.chunks``."""

from __future__ import annotations

import dataclasses

import pytest

from phronesis.providers.chunks import (
    Finish,
    LLMChunk,
    TextChunk,
    ToolCallEnd,
    ToolCallStart,
    ToolResult,
)
from phronesis.providers.usage import TokenUsage


class TestTextChunk:
    def test_holds_text(self) -> None:
        chunk = TextChunk(text="hello")

        assert chunk.text == "hello"

    def test_is_frozen(self) -> None:
        chunk = TextChunk(text="hi")

        with pytest.raises(dataclasses.FrozenInstanceError):
            chunk.text = "bye"  # type: ignore[misc]


class TestToolCallStart:
    def test_holds_call_id_and_name(self) -> None:
        event = ToolCallStart(call_id="c1", tool_name="search")

        assert event.call_id == "c1"
        assert event.tool_name == "search"


class TestToolCallEnd:
    def test_holds_arguments(self) -> None:
        event = ToolCallEnd(call_id="c1", arguments={"q": "phronesis"})

        assert event.arguments == {"q": "phronesis"}


class TestToolResult:
    def test_holds_output(self) -> None:
        event = ToolResult(call_id="c1", output={"hits": 3})

        assert event.output == {"hits": 3}


class TestFinish:
    def test_default_usage_is_none(self) -> None:
        event = Finish(reason="stop")

        assert event.reason == "stop"
        assert event.usage is None

    def test_carries_usage(self) -> None:
        usage = TokenUsage(input_tokens=10, output_tokens=20)
        event = Finish(reason="stop", usage=usage)

        assert event.usage is usage


class TestLLMChunkUnion:
    @pytest.mark.parametrize(
        "chunk",
        [
            TextChunk(text="hi"),
            ToolCallStart(call_id="c", tool_name="t"),
            ToolCallEnd(call_id="c", arguments={}),
            ToolResult(call_id="c", output=None),
            Finish(reason="stop"),
        ],
    )
    def test_dispatch_matches_each_variant(self, chunk: LLMChunk) -> None:
        match chunk:
            case TextChunk():
                kind = "text"
            case ToolCallStart():
                kind = "start"
            case ToolCallEnd():
                kind = "end"
            case ToolResult():
                kind = "result"
            case Finish():
                kind = "finish"

        assert kind in {"text", "start", "end", "result", "finish"}
