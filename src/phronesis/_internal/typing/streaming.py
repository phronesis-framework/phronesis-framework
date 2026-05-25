"""Async streaming primitives for provider responses."""

from __future__ import annotations

from collections.abc import AsyncIterator
from dataclasses import dataclass
from typing import Generic, TypeAlias, TypeVar

T = TypeVar("T")


@dataclass(frozen=True, slots=True)
class StreamChunk(Generic[T]):
    """One chunk emitted by a streaming source, indexed by ``sequence``."""

    payload: T
    sequence: int


Stream: TypeAlias = AsyncIterator[StreamChunk[T]]
"""Async iterator of :class:`StreamChunk` of payload type ``T``."""
