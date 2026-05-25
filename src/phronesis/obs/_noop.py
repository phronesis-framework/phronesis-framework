"""No-op fallbacks used when OpenTelemetry is not installed.

These types satisfy the surface of the public obs API so call sites do
not need to branch on whether the ``obs`` extra is available.

The no-op span is intentionally permissive: it accepts any attribute
value, ignores exception recording and status updates, and supports both
synchronous and asynchronous context manager protocols. This keeps the
public API identical regardless of the runtime environment.
"""

from __future__ import annotations

from types import TracebackType
from typing import Any, Self


class _NoopSpan:
    """Span stand-in that records nothing.

    All instrumentation methods (``set_attribute``, ``set_attributes``,
    ``record_exception``, ``set_status``, ``add_event``, ``end``) accept
    arbitrary arguments and silently discard them.

    The instance is reusable as a synchronous or asynchronous context
    manager and always yields itself.
    """

    __slots__ = ()

    def set_attribute(self, key: str, value: Any) -> None:
        return None

    def set_attributes(self, attributes: dict[str, Any]) -> None:
        return None

    def record_exception(
        self, exception: BaseException, attributes: dict[str, Any] | None = None
    ) -> None:
        return None

    def set_status(self, status: Any, description: str | None = None) -> None:
        return None

    def add_event(self, name: str, attributes: dict[str, Any] | None = None) -> None:
        return None

    def end(self) -> None:
        return None

    def __enter__(self) -> Self:
        return self

    def __exit__(
        self,
        exc_type: type[BaseException] | None,
        exc_value: BaseException | None,
        traceback: TracebackType | None,
    ) -> None:
        return None

    async def __aenter__(self) -> Self:
        return self

    async def __aexit__(
        self,
        exc_type: type[BaseException] | None,
        exc_value: BaseException | None,
        traceback: TracebackType | None,
    ) -> None:
        return None
