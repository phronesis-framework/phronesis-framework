"""Concurrency-specific exceptions."""

from __future__ import annotations

from typing import Any


class ConcurrencyError(Exception):
    """Base class for concurrency-related errors raised by the framework."""


class PartialFailureError(ConcurrencyError):
    """Some tasks in a best-effort gather failed.

    Successful values and exceptions are kept in the original task order:
    if task ``i`` succeeded, ``results[i]`` is its value and
    ``exceptions[i]`` is ``None``; if it failed, ``results[i]`` is ``None``
    and ``exceptions[i]`` is the captured exception.
    """

    def __init__(
        self,
        message: str,
        *,
        results: list[Any],
        exceptions: list[BaseException | None],
    ) -> None:
        super().__init__(message)

        self.results = results
        self.exceptions = exceptions

    @property
    def failed_count(self) -> int:
        return sum(1 for exc in self.exceptions if exc is not None)

    @property
    def successful_count(self) -> int:
        return len(self.exceptions) - self.failed_count
