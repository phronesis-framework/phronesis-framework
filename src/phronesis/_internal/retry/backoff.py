"""Backoff strategies for the retry decorator."""

from __future__ import annotations

import random
from dataclasses import dataclass
from typing import Protocol, runtime_checkable


@runtime_checkable
class BackoffStrategy(Protocol):
    """Maps a 1-based attempt number to a delay in seconds."""

    def get_delay(self, attempt: int) -> float: ...


@dataclass(frozen=True, slots=True)
class FixedBackoff:
    """Constant delay between attempts."""

    delay: float

    def get_delay(self, attempt: int) -> float:  # NOSONAR: protocol conformance
        return self.delay


@dataclass(frozen=True, slots=True)
class ExponentialBackoff:
    """Exponential delay with optional full-jitter.

    Delay grows as ``initial * 2^(attempt - 1)`` capped at ``max_delay``.
    With ``jitter=True`` the final delay is multiplied by ``random.uniform(0.5, 1.5)``.
    """

    initial: float = 1.0
    max_delay: float = 60.0
    jitter: bool = True

    def get_delay(self, attempt: int) -> float:
        base: float = self.initial * (2 ** (attempt - 1))
        capped: float = base if base < self.max_delay else self.max_delay

        if self.jitter:
            return capped * (0.5 + random.random())  # NOSONAR

        return capped
