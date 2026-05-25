"""Read-only budget snapshot exposed through :class:`~phronesis.context.Context`.

MVP shape: tokens and cost remaining. Either or both may be ``None`` when
the runtime does not enforce that particular limit.
"""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True, slots=True)
class Budget:
    """Snapshot of remaining budget at the time a tool is invoked."""

    tokens_remaining: int | None = None
    cost_remaining_usd: float | None = None
