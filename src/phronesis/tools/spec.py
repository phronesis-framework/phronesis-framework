"""Pure data spec for a declared tool.

:class:`ToolSpec` is the immutable, JSON-serialisable side of a tool
declaration. The callable side lives on the :class:`Tool` wrapper,
which exposes the spec via ``tool.spec``. The spec deliberately holds
**no function reference** - the runtime resolves the executable via
the tool registry keyed by :class:`ToolId`.

The spec is suitable for logging, persisting and sharing across
processes (e.g. as part of a discovery payload) without dragging in
the actual implementation.
"""

from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass, field
from types import MappingProxyType
from typing import Any, Final

from phronesis.tools.effects import ToolEffect
from phronesis.tools.tool_id import ToolId, ToolName
from phronesis.tools.version import ToolVersion, parse_version

_EMPTY_SCHEMA: Final[Mapping[str, Any]] = MappingProxyType({})


@dataclass(frozen=True, slots=True)
class ToolSpec:
    """Static, serialisable description of a tool.

    Frozen so it can be shared safely across threads or async tasks.
    Schemas are coerced into :class:`MappingProxyType` in
    ``__post_init__`` so callers cannot mutate them through the
    public attributes.

    Attributes:
        id: Stable internal :class:`ToolId` used as the registry key
            and in observability attribute values.
        name: LLM-facing :class:`ToolName` sent to the provider in
            the tool-definitions list.
        description: Free-form description shown to the model.
        effects: Frozen set of :class:`ToolEffect` values declared by
            the tool. Defaults to the empty set.
        input_schema: Canonical JSON Schema describing the tool's
            arguments. Defaults to the empty mapping.
        output_schema: Optional JSON Schema describing the tool's
            return value. ``None`` means unspecified.
        version: Free-form version string, defaulting to ``"0.1.0"``.
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

        parse_version(self.version)

    @property
    def parsed_version(self) -> ToolVersion:
        """Return :attr:`version` as a strict :class:`ToolVersion`.

        Re-parses on access; cheap and avoids stashing extra state on
        the frozen dataclass. Raises :class:`InvalidVersionError` if
        the version was constructed by bypassing ``__post_init__``.
        """
        return parse_version(self.version)

    def to_dict(self) -> dict[str, Any]:
        """Return a JSON-serialisable representation of the spec.

        Effects are emitted as a sorted list of their string values
        so two equivalent specs always serialise identically.

        Returns:
            A mutable ``dict`` with keys ``id``, ``name``,
            ``description``, ``effects``, ``input_schema``,
            ``output_schema`` and ``version``.
        """
        return {
            "id": self.id.canonical,
            "name": str(self.name),
            "description": self.description,
            "effects": sorted(e.value for e in self.effects),
            "input_schema": dict(self.input_schema),
            "output_schema": (dict(self.output_schema) if self.output_schema is not None else None),
            "version": self.version,
        }
