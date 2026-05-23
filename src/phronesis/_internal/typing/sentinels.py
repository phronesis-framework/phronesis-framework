"""Sentinel values for distinguishing 'not provided' from ``None``.

A sentinel is a singleton object whose only purpose is to mark a slot as
unset in a way that ``None`` cannot. Use these when a function must
distinguish 'caller passed nothing' from 'caller passed ``None``'.

The sentinel is hosted as a single-member :class:`enum.Enum`. This pattern
gives three properties for free:

* Identity uniqueness across the process (enum members are singletons).
* A typed ``Literal`` form usable in annotations and unions.
* A short, descriptive ``repr``.
"""

from enum import Enum
from typing import Final, Literal, TypeAlias


class _MissingEnum(Enum):
    """Single-member enum that hosts the :data:`MISSING` singleton."""

    MISSING = "MISSING"

    def __repr__(self) -> str:  # pragma: no cover - trivial
        return "MISSING"

    def __bool__(self) -> bool:
        return False


MISSING: Final = _MissingEnum.MISSING
"""Sentinel marking an unprovided argument.

Distinct from ``None``. Use identity comparison: ``if x is MISSING``.
"""

MissingType: TypeAlias = Literal[_MissingEnum.MISSING]
"""Type annotation for parameters that accept the :data:`MISSING` sentinel.

Example:
    >>> def fetch(timeout: float | MissingType = MISSING) -> None: ...
"""
