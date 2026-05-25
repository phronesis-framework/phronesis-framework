"""``Maybe[T]`` — explicit optional alternative to ``T | None``."""

from __future__ import annotations

from dataclasses import dataclass
from enum import Enum
from typing import Final, Generic, Literal, TypeAlias, TypeVar

T = TypeVar("T")


class _NothingEnum(Enum):
    NOTHING = "NOTHING"

    def __repr__(self) -> str:  # pragma: no cover - trivial
        return "NOTHING"

    def __bool__(self) -> bool:
        return False


NOTHING: Final = _NothingEnum.NOTHING
"""Absence arm of :data:`Maybe`."""

NothingType: TypeAlias = Literal[_NothingEnum.NOTHING]


@dataclass(frozen=True, slots=True)
class Some(Generic[T]):
    """Presence arm of :data:`Maybe`."""

    value: T


Maybe: TypeAlias = Some[T] | NothingType
"""A value of type ``T`` or :data:`NOTHING`."""
