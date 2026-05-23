"""Per-attempt accounting captured by the retry decorator."""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True, slots=True)
class AttemptInfo:
    """One row in the retry history.

    ``delay_before_next_ms`` is ``None`` for the final attempt (no further wait).
    """

    attempt_number: int
    exception: Exception | None
    duration_ms: float
    delay_before_next_ms: float | None
