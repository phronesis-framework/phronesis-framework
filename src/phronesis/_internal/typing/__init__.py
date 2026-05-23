"""Typing primitives shared across the framework.

This package bundles small, focused type primitives used by every layer.

Design rules:

* No Pydantic in this package. Pydantic is for data validation at the
  boundary; these primitives are pure typing.
* Prefer ``dataclass(frozen=True, slots=True)`` for value objects so they
  are immutable, hashable when their fields are, and cheap on hot paths.
* No runtime overhead beyond what stdlib provides.
"""

from phronesis._internal.typing.json import JsonArray, JsonObject, JsonValue

__all__ = ["JsonArray", "JsonObject", "JsonValue"]
