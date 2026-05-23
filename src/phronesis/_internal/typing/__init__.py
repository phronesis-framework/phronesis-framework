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
from phronesis._internal.typing.maybe import NOTHING, Maybe, NothingType, Some
from phronesis._internal.typing.newtypes import (
    ByteSize,
    CompletionTokens,
    Cost,
    Milliseconds,
    PromptTokens,
    Seconds,
    TokenCount,
)
from phronesis._internal.typing.protocols import Identifiable, SupportsJson
from phronesis._internal.typing.result import Err, Ok, Result
from phronesis._internal.typing.sentinels import MISSING, MissingType
from phronesis._internal.typing.streaming import Stream, StreamChunk

__all__ = [
    "MISSING",
    "NOTHING",
    "ByteSize",
    "CompletionTokens",
    "Cost",
    "Err",
    "Identifiable",
    "JsonArray",
    "JsonObject",
    "JsonValue",
    "Maybe",
    "Milliseconds",
    "MissingType",
    "NothingType",
    "Ok",
    "PromptTokens",
    "Result",
    "Seconds",
    "Some",
    "Stream",
    "StreamChunk",
    "SupportsJson",
    "TokenCount",
]
