"""Identifier types for tools.

Tools carry two identifiers with different audiences. :class:`ToolId`
is the internal, stable, framework-side handle (used for registry
lookups, audit logs and id-based wiring). :class:`ToolName` is the
LLM-facing, human-readable label sent to providers, kept distinct so
renames in the UI never break internal references.
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
