"""Closed vocabulary of declarable side-effects for a tool.

See ``docs/TOOLS-DECISIONS.md`` (D-10, D-11): the vocabulary is closed
and framework-owned. Users cannot invent new effects; if a new category
is needed, it is added here.
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
