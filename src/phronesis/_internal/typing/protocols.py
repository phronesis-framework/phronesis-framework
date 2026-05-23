"""Structural :class:`typing.Protocol` contracts.

Protocols capture behavioural shape: 'whoever implements these methods is
acceptable here'. Pydantic models capture data shape: 'these fields are
present and validated'. Keep the two distinct — Protocols are for
behaviour, not for data validation.

All protocols here are :func:`typing.runtime_checkable` so they can be
used with :func:`isinstance` at boundary checks. Be aware of the standard
limitation: ``isinstance`` against a runtime-checkable Protocol only
verifies attribute presence, not type signatures.
"""

from __future__ import annotations

from typing import Protocol, runtime_checkable

from phronesis._internal.typing.json import JsonValue

__all__ = ["Identifiable", "SupportsJson"]


@runtime_checkable
class SupportsJson(Protocol):
    """An object that can be serialised to a :data:`JsonValue`.

    Implementations should return a structure that is JSON-representable
    by ``json.dumps`` without custom encoders.
    """

    def to_json(self) -> JsonValue: ...


@runtime_checkable
class Identifiable(Protocol):
    """An object that exposes a stable string identifier."""

    @property
    def id(self) -> str: ...
