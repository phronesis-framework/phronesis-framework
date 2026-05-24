"""LLM-facing error hierarchy for tools.

See ``docs/TOOLS-DECISIONS.md`` (D-13): errors in this hierarchy are
serialized back to the model so it can react. Any other exception
escapes to the runtime for policy or abort.
"""

from __future__ import annotations

import asyncio
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


class ToolDefinitionError(ToolError):
    """A tool definition is structurally invalid (decoration-time error)."""

    code = "tool_definition_error"


def auto_map_exception(exc: BaseException) -> ToolError | None:
    """Map a small, closed set of standard exceptions to :class:`ToolError`.

    See ``docs/TOOLS-DECISIONS.md`` (D-14). Returns ``None`` for anything
    outside the allowlist so the runtime can apply its own policies.

    Cancellation and interpreter-level signals never reach this function:
    the caller is expected to re-raise ``BaseException`` subclasses that
    are not ``Exception`` before delegating here.
    """
    if isinstance(exc, ToolError):
        return exc

    if isinstance(exc, FileNotFoundError):
        return ToolNotFoundError(
            str(exc) or "file not found",
            details={"path": exc.filename} if exc.filename is not None else {},
        )

    if isinstance(exc, PermissionError):
        return ToolPermissionError(
            str(exc) or "permission denied",
            details={"path": exc.filename} if exc.filename is not None else {},
        )

    if isinstance(exc, (TimeoutError, asyncio.TimeoutError)):
        return ToolTimeoutError(str(exc) or "operation timed out")

    mapped = _map_pydantic_validation_error(exc)

    if mapped is not None:
        return mapped

    mapped = _map_httpx_status_error(exc)

    if mapped is not None:
        return mapped

    return None


def _map_pydantic_validation_error(exc: BaseException) -> ToolError | None:
    try:
        from pydantic import ValidationError
    except ImportError:
        return None

    if not isinstance(exc, ValidationError):
        return None

    return ToolValidationError(
        str(exc),
        details={"errors": exc.errors()},
    )


def _map_httpx_status_error(exc: BaseException) -> ToolError | None:
    try:
        from httpx import HTTPStatusError
    except ImportError:
        return None

    if not isinstance(exc, HTTPStatusError):
        return None

    status_code = exc.response.status_code

    if not (400 <= status_code < 500):
        return None

    return ToolHTTPError(
        str(exc),
        details={
            "status_code": status_code,
            "url": str(exc.request.url),
        },
    )
