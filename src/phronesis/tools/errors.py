"""LLM-facing error hierarchy for tools.

Every error in this hierarchy is intended to be serialised back to
the model so it can react and try again. Any exception that is
**not** a :class:`ToolError` (and is not caught by
:func:`auto_map_exception`) escapes to the agent loop, where it is
wrapped in :class:`phronesis.agents.errors.AgentExecutionError` and
aborts the run.

Each subclass carries a stable, machine-readable ``code`` attribute so
the model receives a deterministic identifier alongside the human
message in the serialised payload produced by :meth:`ToolError.to_dict`.

:func:`auto_map_exception` translates a small, closed set of standard
exceptions into the corresponding :class:`ToolError` so common cases
(file not found, permission denied, timeouts, ``pydantic.ValidationError``,
``httpx`` 4xx responses) behave correctly without per-tool boilerplate.
:class:`SchemaDegradationWarning` is emitted when a provider adapter
loses or coerces information from the canonical schema.
"""

from __future__ import annotations

import asyncio
from typing import Any


class ToolError(Exception):
    """Base class for errors that are serialised back to the LLM.

    Attributes:
        code: Stable, machine-readable error identifier. Subclasses
            override this with their own constant value.
        message: Human-readable description of the error.
        details: Free-form structured payload (e.g. failing field,
            file path, status code) included in the serialised form.
    """

    code: str = "tool_error"

    def __init__(
        self,
        message: str,
        *,
        details: dict[str, Any] | None = None,
    ) -> None:
        """Build a tool error.

        Args:
            message: Human-readable description.
            details: Optional dictionary of structured diagnostic
                data. Copied so caller mutation cannot leak in.
        """
        super().__init__(message)
        self.message = message
        self.details: dict[str, Any] = dict(details) if details else {}

    def to_dict(self) -> dict[str, Any]:
        """Return a JSON-serialisable representation for the LLM.

        Returns:
            ``{"error": code, "message": message, "details": details}``.
            Suitable for direct inclusion in a tool-result block.
        """
        return {
            "error": self.code,
            "message": self.message,
            "details": self.details,
        }


class ToolValidationError(ToolError):
    """Arguments did not match the tool's input schema.

    Raised by the dynamic pydantic validator when arguments produced
    by the model fail to coerce into the expected types. The
    ``details`` payload includes the offending ``field`` and, when
    available, the expected schema for that field only.
    """

    code = "tool_validation_error"


class ToolNotFoundError(ToolError):
    """The tool or a resource it references could not be found.

    Used both by the registry (unknown :class:`ToolId`) and by
    :func:`auto_map_exception` for built-in :class:`FileNotFoundError`.
    """

    code = "tool_not_found"


class ToolTimeoutError(ToolError):
    """Tool execution exceeded its allotted time budget.

    Emitted directly by tools that enforce their own deadlines or
    derived from standard :class:`TimeoutError`/``asyncio.TimeoutError``
    by :func:`auto_map_exception`.
    """

    code = "tool_timeout"


class ToolPermissionError(ToolError):
    """Tool was denied access to a required resource.

    Used both for explicit permission failures and as the mapped form
    of the built-in :class:`PermissionError`.
    """

    code = "tool_permission_denied"


class ToolHTTPError(ToolError):
    """A downstream HTTP call returned a client-side (4xx) status.

    Derived from ``httpx.HTTPStatusError`` by :func:`auto_map_exception`
    when the response status is in the 4xx range. Server-side (5xx)
    errors are intentionally **not** mapped — those typically indicate
    a transient condition that the runtime should retry, not a
    failure to surface to the model.
    """

    code = "tool_http_error"


class DuplicateToolError(ToolError):
    """Two distinct tools were registered under the same canonical id.

    Raised by :meth:`_ToolRegistry.register` when an id is reused.
    Re-registering the same instance is a no-op.
    """

    code = "duplicate_tool"


class ToolDefinitionError(ToolError):
    """A tool definition is structurally invalid.

    Raised at decoration time — for instance when the decorated
    function declares more than one :class:`Context`-typed parameter.
    """

    code = "tool_definition_error"


class UnsupportedProviderError(ToolError):
    """No adapter is registered for the requested provider.

    Raised by ``phronesis.tools.providers.get_adapter`` and surfaced
    from :meth:`Tool.get_schema` when the caller asks for a provider
    that the registry does not know about.
    """

    code = "unsupported_provider"


class SchemaDegradationWarning(UserWarning):
    """A provider adapter lost or coerced information from the canonical schema.

    Informational; the adapted schema is still returned. Promote with
    :mod:`warnings.filterwarnings` if a stricter policy is desired.
    """


def auto_map_exception(exc: BaseException) -> ToolError | None:
    """Map a small, closed set of standard exceptions to :class:`ToolError`.

    The function is called by :class:`Tool` immediately around the
    invocation of the wrapped callable. It covers the common cases
    that almost every tool benefits from without writing per-tool
    try/except blocks:

    * existing :class:`ToolError` instances are returned unchanged;
    * :class:`FileNotFoundError` → :class:`ToolNotFoundError`;
    * :class:`PermissionError` → :class:`ToolPermissionError`;
    * :class:`TimeoutError` / ``asyncio.TimeoutError`` →
      :class:`ToolTimeoutError`;
    * ``pydantic.ValidationError`` → :class:`ToolValidationError`
      (when pydantic is importable);
    * ``httpx.HTTPStatusError`` with a 4xx status →
      :class:`ToolHTTPError` (when httpx is importable).

    Cancellation and interpreter-level signals never reach this
    function: callers are expected to re-raise ``BaseException``
    subclasses that are not ``Exception`` before delegating here.

    Args:
        exc: The exception raised by the tool callable.

    Returns:
        A :class:`ToolError` if ``exc`` is in the allowlist, otherwise
        ``None`` so the runtime can apply its own policy.
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
