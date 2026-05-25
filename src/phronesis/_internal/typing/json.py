"""Recursive type aliases for JSON-representable values."""

from __future__ import annotations

from typing import TypeAlias

JsonArray: TypeAlias = list["JsonValue"]
JsonObject: TypeAlias = dict[str, "JsonValue"]
JsonValue: TypeAlias = str | int | float | bool | None | JsonArray | JsonObject
