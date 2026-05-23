"""``Result[T, E]`` — a tagged union for typed success or failure.

A ``Result`` is either :class:`Ok` carrying a value of type ``T`` or
:class:`Err` carrying an error of type ``E``. Consume it with pattern
matching:

    match result:
        case Ok(value):
            ...
        case Err(error):
            ...

Use ``Result`` when a function can fail with information the caller needs
to inspect. For programming errors and unexpected failures, raise instead.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Generic, TypeAlias, TypeVar

T = TypeVar("T")
E = TypeVar("E")


@dataclass(frozen=True, slots=True)
class Ok(Generic[T]):
    """Success arm of a :data:`Result`."""

    value: T


@dataclass(frozen=True, slots=True)
class Err(Generic[E]):
    """Failure arm of a :data:`Result`."""

    error: E


Result: TypeAlias = Ok[T] | Err[E]
"""A computation that yielded a value of type ``T`` or failed with ``E``."""
