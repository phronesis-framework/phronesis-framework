"""Structural contracts shared across the framework."""

from __future__ import annotations

from typing import Protocol, runtime_checkable

from phronesis._internal.typing.json import JsonValue


@runtime_checkable
class SupportsJson(Protocol):
    """An object that can be serialised to a :data:`JsonValue`."""

    def to_json(self) -> JsonValue: ...


@runtime_checkable
class Identifiable(Protocol):
    """An object that exposes a stable string identifier."""

    @property
    def id(self) -> str: ...
