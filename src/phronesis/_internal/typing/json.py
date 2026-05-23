"""Type aliases for JSON-representable values.

These are static-only aliases. They model the shape of values that cross
serialization boundaries (tool I/O, specs, traces, persisted state), but
perform no runtime validation by themselves. Static type checkers (mypy)
enforce them at compile time; runtime checks live elsewhere.

The aliases are mutually recursive: a ``JsonValue`` is either a primitive,
a ``JsonArray`` of values, or a ``JsonObject`` mapping strings to values.
"""

from __future__ import annotations

from typing import TypeAlias

JsonArray: TypeAlias = list["JsonValue"]
"""Ordered sequence of JSON values."""

JsonObject: TypeAlias = dict[str, "JsonValue"]
"""String-keyed mapping of JSON values."""

JsonValue: TypeAlias = str | int | float | bool | None | JsonArray | JsonObject
"""Any value representable in JSON: primitive, array, or object."""
