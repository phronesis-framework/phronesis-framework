"""Base class for definition-time identifiers."""

import hashlib
from dataclasses import dataclass
from typing import ClassVar

from phronesis._internal.ids.validator import CanonicalIdValidator


@dataclass(frozen=True, slots=True)
class Id:
    """Stable identifier for a declared entity.

    Subclasses set :attr:`prefix` (e.g. ``"TID"`` for tools, ``"AID"`` for
    agents). :attr:`canonical` is the validated identity string;
    :attr:`short` is a compact ``<PREFIX>-XXXXXXXX`` hash for display.
    """

    canonical: str
    prefix: ClassVar[str] = ""

    def __post_init__(self) -> None:
        if not self.prefix:
            raise TypeError(f"{type(self).__name__} must define a non-empty `prefix`.")
        CanonicalIdValidator.validate(self.canonical)

    @property
    def short(self) -> str:
        """``<PREFIX>-XXXXXXXX`` where ``XXXXXXXX`` is the SHA-256 prefix."""
        digest = hashlib.sha256(self.canonical.encode()).hexdigest()
        return f"{self.prefix}-{digest[:8].upper()}"

    def __str__(self) -> str:
        return self.canonical

    def __repr__(self) -> str:
        return f"{type(self).__name__}({self.canonical!r})"
