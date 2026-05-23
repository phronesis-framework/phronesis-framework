"""Tests for streaming primitives."""

import asyncio
from dataclasses import FrozenInstanceError

import pytest

from phronesis._internal.typing import Stream, StreamChunk


class TestStreamChunk:
    def test_holds_payload_and_sequence(self) -> None:
        chunk: StreamChunk[str] = StreamChunk(payload="hello", sequence=0)

        assert chunk.payload == "hello"
        assert chunk.sequence == 0

    def test_is_frozen(self) -> None:
        chunk: StreamChunk[str] = StreamChunk(payload="x", sequence=0)

        with pytest.raises(FrozenInstanceError):
            chunk.payload = "y"  # type: ignore[misc]

    def test_equality_by_fields(self) -> None:
        a = StreamChunk(payload="x", sequence=0)
        b = StreamChunk(payload="x", sequence=0)
        c = StreamChunk(payload="x", sequence=1)

        assert a == b
        assert a != c


class TestStream:
    def test_can_be_consumed_as_async_iterator(self) -> None:
        async def producer() -> Stream[str]:
            for i, text in enumerate(["a", "b", "c"]):
                yield StreamChunk(payload=text, sequence=i)

        async def consume() -> list[tuple[str, int]]:
            collected: list[tuple[str, int]] = []

            async for chunk in producer():
                collected.append((chunk.payload, chunk.sequence))

            return collected

        assert asyncio.run(consume()) == [("a", 0), ("b", 1), ("c", 2)]
