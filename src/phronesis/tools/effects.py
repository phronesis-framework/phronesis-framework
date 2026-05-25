"""Closed vocabulary of declarable side-effects for a tool.

The vocabulary is closed and framework-owned: users cannot invent new
effects on the fly. If a new category is needed, it is added to
:class:`ToolEffect` so every tool and every policy stays aligned.
"""

from __future__ import annotations

from enum import StrEnum


class ToolEffect(StrEnum):
    """Enumeration of effects a tool may declare.

    Member names follow Python conventions (SCREAMING_SNAKE_CASE) while
    serialized values are the canonical, stable strings used in logs,
    JSON payloads, and audit records.
    """

    NETWORK = "network"
    FILESYSTEM_READ = "filesystem.read"
    FILESYSTEM_WRITE = "filesystem.write"
    SIDE_EFFECT = "side-effect"
    EXPENSIVE = "expensive"
    LONG_RUNNING = "long-running"
    REQUIRES_CONFIRMATION = "requires-confirmation"
