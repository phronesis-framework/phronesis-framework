"""Public API of the :mod:`phronesis.tools` package.

This module re-exports the names that constitute the supported tools
surface. Anything not listed here is internal and subject to change
without notice.
"""

from __future__ import annotations

from phronesis.context.context import Context
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

__all__ = [
    "Context",
    "DuplicateToolError",
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
    "UnsupportedProviderError",
    "auto_map_exception",
    "current_registry",
    "discover",
    "tool",
    "tool_scope",
]
