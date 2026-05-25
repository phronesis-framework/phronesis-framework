"""Exceptions raised by the retry decorator."""

from __future__ import annotations

from .attempt import AttemptInfo


class RetryError(Exception):
    """Base class for retry-related errors."""


class RetryExhaustedError(RetryError):
    """All retry attempts were used without success."""

    def __init__(
        self,
        *,
        attempts: int,
        total_duration_ms: float,
        last_exception: Exception,
        attempt_history: list[AttemptInfo],
    ) -> None:
        super().__init__(f"retries exhausted after {attempts} attempts")
        self.attempts = attempts
        self.total_duration_ms = total_duration_ms
        self.last_exception = last_exception
        self.attempt_history = attempt_history
