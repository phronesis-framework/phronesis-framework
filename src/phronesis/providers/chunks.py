"""Streaming chunk types.

See ``docs/PROVIDERS-DECISIONS.md`` (D-08): a sealed union of frozen,
slotted dataclasses. Each subtype models a distinct event a provider
emits during streaming.

Consumers can ``match`` on the union exhaustively; the type checker
flags missing variants.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from phronesis.providers.usage import TokenUsage


@dataclass(frozen=True, slots=True)
class TextChunk:
    """A piece of generated text."""

    text: str


@dataclass(frozen=True, slots=True)
class ToolCallStart:
    """A tool invocation is starting; arguments are not yet known."""

    call_id: str
    tool_name: str


@dataclass(frozen=True, slots=True)
class ToolCallEnd:
    """A tool invocation finished; the full argument dict is available."""

    call_id: str
    arguments: dict[str, Any]


@dataclass(frozen=True, slots=True)
class ToolResult:
    """The result of a tool invocation, as reported back to the model."""

    call_id: str
    output: Any


@dataclass(frozen=True, slots=True)
class Finish:
    """Terminal event of a stream."""

    reason: str
    usage: TokenUsage | None = None


LLMChunk = TextChunk | ToolCallStart | ToolCallEnd | ToolResult | Finish
