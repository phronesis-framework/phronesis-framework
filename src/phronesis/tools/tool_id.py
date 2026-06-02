"""Identifier types for tools.

Every declared tool carries two distinct identifiers:

* :class:`ToolId` - the stable, framework-side canonical id used as
  the registry key and as the value of observability attributes. It is
  derived from the declaring function's dotted path and is opaque to
  the model.
* :class:`ToolName` - the LLM-facing, human-readable name. It defaults
  to the function's ``__name__`` but can be overridden on the
  :func:`tool` decorator.

:data:`tool_id_generator` is a process-wide singleton useful for
parsing and validating canonical strings.
"""

from __future__ import annotations

from typing import NewType

from phronesis._internal.ids.generator import IdGenerator
from phronesis._internal.ids.id import Id

ToolName = NewType("ToolName", str)


class ToolId(Id):
    """Stable internal identifier for a declared tool.

    Subclass of :class:`phronesis._internal.ids.id.Id` with the short
    prefix ``"TID"``. Instances are created from a canonical string
    (e.g. ``"phronesis.tools.example.ping"``) and validated by the
    base class.
    """

    prefix = "TID"


tool_id_generator: IdGenerator[ToolId] = IdGenerator(ToolId)
"""Process-wide :class:`IdGenerator` bound to :class:`ToolId`.

Use ``tool_id_generator.from_canonical(text)`` to validate and parse a
canonical tool id without instantiating a generator yourself.
"""
