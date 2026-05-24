"""LLM-facing error hierarchy for tools.

See ``docs/TOOLS-DECISIONS.md`` (D-13): errors in this hierarchy are
serialized back to the model so it can react. Any other exception
escapes to the runtime for policy or abort.
"""

from __future__ import annotations

from typing import Any


class ToolError(Exception):
    """Base class for errors that are serialized back to the LLM.

    Subclasses set a stable ``code`` so the model receives a
    machine-readable identifier alongside the message.
    """

    code: str = "tool_error"

    def __init__(
        self,
        message: str,
        *,
        details: dict[str, Any] | None = None,
    ) -> None:
        super().__init__(message)
        self.message = message
        self.details: dict[str, Any] = dict(details) if details else {}

    def to_dict(self) -> dict[str, Any]:
        """Return a JSON-serializable representation for the LLM."""
        return {
            "error": self.code,
            "message": self.message,
            "details": self.details,
        }


class ToolValidationError(ToolError):
    """Arguments did not match the tool's input schema."""

    code = "tool_validation_error"


class ToolNotFoundError(ToolError):
    """Tool or resource referenced by the tool was not found."""

    code = "tool_not_found"


class ToolTimeoutError(ToolError):
    """Tool execution exceeded its allotted time budget."""

    code = "tool_timeout"


class ToolPermissionError(ToolError):
    """Tool was denied access to a required resource."""

    code = "tool_permission_denied"


class ToolHTTPError(ToolError):
    """A downstream HTTP call returned a client-side (4xx) status."""

    code = "tool_http_error"


class DuplicateToolError(ToolError):
    """Two distinct tools were registered under the same canonical id."""

    code = "duplicate_tool"
