"""Small typing primitives shared across the framework."""

from phronesis._internal.typing.binary import BinaryContent
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
    "BinaryContent",
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
