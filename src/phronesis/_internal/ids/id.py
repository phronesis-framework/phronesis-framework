"""Base for definition-time identifiers.

A definition id is the stable, derivable identifier of an entity declared
in code (a tool, an agent, a pipeline, etc.). It exposes:

- `canonical`: the stable identity used internally and in serialized specs.
- `short`: a compact, human-readable representation prefixed by entity type.

Subclasses only declare the prefix.
"""

import hashlib
from dataclasses import dataclass
from typing import ClassVar

from phronesis._internal.ids.validator import CanonicalIdValidator


@dataclass(frozen=True, slots=True)
class Id:
    """Stable identifier for a declared entity.

    Subclasses must override `prefix` with their entity type prefix
    (e.g. "TID" for tools, "AID" for agents).
    """

    canonical: str
    prefix: ClassVar[str] = ""

    def __post_init__(self) -> None:
        if not self.prefix:
            raise TypeError(f"{type(self).__name__} must define a non-empty `prefix`.")
        CanonicalIdValidator.validate(self.canonical)

    @property
    def short(self) -> str:
        """Short representation: <PREFIX>-XXXXXXXX (SHA-256 truncated)."""
        digest = hashlib.sha256(self.canonical.encode()).hexdigest()
        return f"{self.prefix}-{digest[:8].upper()}"

    def __str__(self) -> str:
        return self.canonical

    def __repr__(self) -> str:
        return f"{type(self).__name__}({self.canonical!r})"
