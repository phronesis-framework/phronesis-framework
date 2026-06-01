"""Public API of the :mod:`phronesis.tools` package.

This package provides everything needed to declare, register, validate
and serialise tools that an LLM can call:

* :class:`Tool` and the :func:`tool` decorator declare new tools.
* :class:`ToolSpec` is the pure-data description of a tool.
* :class:`ToolEffect` is the closed vocabulary of declarable
  side-effects.
* :func:`discover` walks a package tree to trigger eager registration.
* :func:`tool_scope` and :func:`current_registry` give per-context
  isolation of declared tools.
* :class:`Context` is re-exported so tools can type-annotate the
  runtime context parameter.
* The ``Tool*Error`` hierarchy plus :func:`auto_map_exception` cover
  every diagnostic the package raises; :class:`SchemaDegradationWarning`
  is emitted when a provider adapter loses fidelity from the canonical
  schema.

Only names listed in ``__all__`` are part of the public contract.
Anything else is internal and may change without notice.
"""

from __future__ import annotations

from phronesis.context.context import Context
from phronesis.tools.cache import CachePolicy
from phronesis.tools.decorator import tool
from phronesis.tools.discover import discover
from phronesis.tools.effects import ToolEffect
from phronesis.tools.errors import (
    DuplicateToolError,
    SchemaDegradationWarning,
    ToolDefinitionError,
    ToolError,
    ToolHTTPError,
    ToolNotFoundError,
    ToolPermissionError,
    ToolTimeoutError,
    ToolValidationError,
    UnsupportedProviderError,
    auto_map_exception,
)
from phronesis.tools.registry import current_registry, tool_scope
from phronesis.tools.spec import ToolSpec
from phronesis.tools.tool import Tool
from phronesis.tools.tool_id import ToolId, ToolName
from phronesis.tools.version import InvalidVersionError, ToolVersion, parse_version

__all__ = [
    "CachePolicy",
    "Context",
    "DuplicateToolError",
    "InvalidVersionError",
    "SchemaDegradationWarning",
    "Tool",
    "ToolDefinitionError",
    "ToolEffect",
    "ToolError",
    "ToolHTTPError",
    "ToolId",
    "ToolName",
    "ToolNotFoundError",
    "ToolPermissionError",
    "ToolSpec",
    "ToolTimeoutError",
    "ToolValidationError",
    "ToolVersion",
    "UnsupportedProviderError",
    "auto_map_exception",
    "current_registry",
    "discover",
    "parse_version",
    "tool",
    "tool_scope",
]
