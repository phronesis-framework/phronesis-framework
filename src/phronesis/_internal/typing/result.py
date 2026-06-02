"""``Result[T, E]`` - tagged union for typed success or failure."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Generic, TypeAlias, TypeVar

T = TypeVar("T")
E = TypeVar("E")


@dataclass(frozen=True, slots=True)
class Ok(Generic[T]):
    """Success arm of :data:`Result`."""

    value: T


@dataclass(frozen=True, slots=True)
class Err(Generic[E]):
    """Failure arm of :data:`Result`."""

    error: E


Result: TypeAlias = Ok[T] | Err[E]
"""A value of type ``T`` or a failure of type ``E``."""
