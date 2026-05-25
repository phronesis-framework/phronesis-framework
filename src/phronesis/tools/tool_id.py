"""Identifier types for tools.

See ``docs/TOOLS-DECISIONS.md`` (D-04, D-05): tools carry two
identifiers — :class:`ToolId` (internal, stable, framework-side) and
:class:`ToolName` (LLM-facing, human-readable).
"""

from __future__ import annotations

from typing import NewType

from phronesis._internal.ids.generator import IdGenerator
from phronesis._internal.ids.id import Id

ToolName = NewType("ToolName", str)


class ToolId(Id):
    """Stable internal identifier for a declared tool."""

    prefix = "TID"


tool_id_generator: IdGenerator[ToolId] = IdGenerator(ToolId)
"""Singleton :class:`IdGenerator` for :class:`ToolId`."""
