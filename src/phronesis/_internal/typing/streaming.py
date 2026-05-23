"""Async streaming primitives for token-level provider responses.

A :class:`StreamChunk` is a single piece emitted by a streaming source
(token text, content delta, event). A :data:`Stream` is the asynchronous
iterator of such chunks.

Use this typing shape at the provider boundary; richer per-chunk payloads
(deltas, tool-call fragments) are modelled by domain-specific dataclasses
or Pydantic models that consumers parameterise into ``StreamChunk[T]``.
"""

from __future__ import annotations

from collections.abc import AsyncIterator
from dataclasses import dataclass
from typing import Generic, TypeAlias, TypeVar

__all__ = ["Stream", "StreamChunk"]

T = TypeVar("T")


@dataclass(frozen=True, slots=True)
class StreamChunk(Generic[T]):
    """A single chunk emitted by a streaming source.

    Attributes:
        payload: The chunk content of arbitrary parameterised type ``T``.
        sequence: Monotonically increasing index assigned by the producer.
    """

    payload: T
    sequence: int


Stream: TypeAlias = AsyncIterator[StreamChunk[T]]
"""An asynchronous iterator of :class:`StreamChunk` of payload type ``T``."""
