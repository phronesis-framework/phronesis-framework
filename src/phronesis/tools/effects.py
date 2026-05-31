"""Closed vocabulary of declarable side-effects for a tool.

A tool declares its effects via the ``effects=`` argument of the
:func:`tool` decorator. The vocabulary is intentionally closed and
framework-owned: callers cannot invent new categories. If a new effect
is needed it must be added here so policy code (rate limits,
permission checks, audit pipelines, etc.) can rely on a fixed set of
known values.

Serialised values use stable, hyphen-and-dot identifiers suitable for
log lines, JSON payloads and audit records.
"""

from __future__ import annotations

from enum import StrEnum


class ToolEffect(StrEnum):
    """Enumeration of effects a tool may declare.

    Member names follow Python conventions (SCREAMING_SNAKE_CASE)
    while serialised values are the canonical, stable strings used in
    logs, JSON payloads and audit records. The enum subclasses
    :class:`StrEnum` so members compare equal to their string values.

    Attributes:
        NETWORK: The tool issues outbound network calls.
        FILESYSTEM_READ: The tool reads from the local filesystem.
        FILESYSTEM_WRITE: The tool writes to the local filesystem.
        SIDE_EFFECT: The tool produces non-idempotent side-effects
            (sending email, mutating an external system, etc.).
        EXPENSIVE: The tool is meaningfully costly (paid API, heavy
            compute, etc.).
        LONG_RUNNING: The tool may take a long time to return.
        REQUIRES_CONFIRMATION: Policy code must obtain user
            confirmation before invoking the tool.
    """

    NETWORK = "network"
    FILESYSTEM_READ = "filesystem.read"
    FILESYSTEM_WRITE = "filesystem.write"
    SIDE_EFFECT = "side-effect"
    EXPENSIVE = "expensive"
    LONG_RUNNING = "long-running"
    REQUIRES_CONFIRMATION = "requires-confirmation"
