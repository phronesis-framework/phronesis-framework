"""``Maybe[T]`` — an explicit optional alternative to ``Optional[T]``.

A ``Maybe`` is either :class:`Some` carrying a value of type ``T`` or the
:data:`NOTHING` sentinel. Using ``Maybe`` makes the optional nature
visible at call sites and removes the ambiguity of ``None`` (which can
mean 'absent' or a legitimate domain value).

Consume with pattern matching:

    match opt:
        case Some(value):
            ...
        case _:
            # NOTHING
            ...
"""

from __future__ import annotations

from dataclasses import dataclass
from enum import Enum
from typing import Final, Generic, Literal, TypeAlias, TypeVar

__all__ = ["NOTHING", "Maybe", "NothingType", "Some"]

T = TypeVar("T")


class _NothingEnum(Enum):
    """Single-member enum that hosts the :data:`NOTHING` singleton."""

    NOTHING = "NOTHING"

    def __repr__(self) -> str:  # pragma: no cover - trivial
        return "NOTHING"

    def __bool__(self) -> bool:
        return False


NOTHING: Final = _NothingEnum.NOTHING
"""Absence arm of a :data:`Maybe`."""

NothingType: TypeAlias = Literal[_NothingEnum.NOTHING]
"""Type annotation for the :data:`NOTHING` sentinel."""


@dataclass(frozen=True, slots=True)
class Some(Generic[T]):
    """Presence arm of a :data:`Maybe`."""

    value: T


Maybe: TypeAlias = Some[T] | NothingType
"""A value of type ``T`` or :data:`NOTHING`."""
