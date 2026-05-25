"""``MISSING`` sentinel for distinguishing "not provided" from ``None``."""

from enum import Enum
from typing import Final, Literal, TypeAlias


class _MissingEnum(Enum):
    MISSING = "MISSING"

    def __repr__(self) -> str:  # pragma: no cover - trivial
        return "MISSING"

    def __bool__(self) -> bool:
        return False


MISSING: Final = _MissingEnum.MISSING
"""Singleton marking an unprovided argument. Compare with ``is MISSING``."""

MissingType: TypeAlias = Literal[_MissingEnum.MISSING]
"""Type alias for parameters that accept :data:`MISSING`."""
