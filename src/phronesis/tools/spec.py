"""Pure data spec for a declared tool.

:class:`ToolSpec` is frozen and JSON-serializable, and intentionally
holds **no function reference**. The callable side of a tool lives on
the :class:`Tool` object itself; ``tool.spec`` exposes only the inert
data half (id, name, description, effects, schemas, version) so it can
be shipped to providers, audit logs and registries without dragging the
runtime closure along.
"""

from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass, field
from types import MappingProxyType
from typing import Any, Final

from phronesis.tools.effects import ToolEffect
from phronesis.tools.tool_id import ToolId, ToolName

_EMPTY_SCHEMA: Final[Mapping[str, Any]] = MappingProxyType({})


@dataclass(frozen=True, slots=True)
class ToolSpec:
    """Static, serializable description of a tool.

    The runtime resolves the executable via :class:`ToolId`; the spec
    itself never holds the function reference.
    """

    id: ToolId
    name: ToolName
    description: str
    effects: frozenset[ToolEffect] = frozenset()
    input_schema: Mapping[str, Any] = field(default_factory=lambda: _EMPTY_SCHEMA)
    output_schema: Mapping[str, Any] | None = None
    version: str = "0.1.0"

    def __post_init__(self) -> None:
        if not isinstance(self.input_schema, MappingProxyType):
            object.__setattr__(
                self,
                "input_schema",
                MappingProxyType(dict(self.input_schema)),
            )

        if self.output_schema is not None and not isinstance(self.output_schema, MappingProxyType):
            object.__setattr__(
                self,
                "output_schema",
                MappingProxyType(dict(self.output_schema)),
            )

    def to_dict(self) -> dict[str, Any]:
        """Return a JSON-serializable representation of the spec."""
        return {
            "id": self.id.canonical,
            "name": str(self.name),
            "description": self.description,
            "effects": sorted(e.value for e in self.effects),
            "input_schema": dict(self.input_schema),
            "output_schema": (dict(self.output_schema) if self.output_schema is not None else None),
            "version": self.version,
        }
