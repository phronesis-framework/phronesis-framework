"""Streaming chunk types.

:data:`LLMChunk` is a sealed union of frozen, slotted dataclasses
where each variant models a distinct event a provider emits while
streaming a response. Consumers can ``match`` on the union
exhaustively; the type checker flags missing variants if a new event
type is added later.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from phronesis.providers.usage import TokenUsage


@dataclass(frozen=True, slots=True)
class TextChunk:
    """A piece of generated text.

    Attributes:
        text: Incremental text fragment. May be empty when the
            vendor emits a heartbeat-style event.
    """

    text: str


@dataclass(frozen=True, slots=True)
class ToolCallStart:
    """A tool invocation is starting; arguments are not yet known.

    Attributes:
        call_id: Provider-assigned identifier later echoed by the
            matching :class:`ToolCallEnd` and :class:`ToolResult`.
        tool_name: LLM-facing tool name the model decided to call.
    """

    call_id: str
    tool_name: str


@dataclass(frozen=True, slots=True)
class ToolCallEnd:
    """A tool invocation finished; the full argument dict is available.

    Attributes:
        call_id: Matches the originating :class:`ToolCallStart`.
        arguments: Decoded JSON arguments produced by the model.
    """

    call_id: str
    arguments: dict[str, Any]


@dataclass(frozen=True, slots=True)
class ToolResult:
    """The result of a tool invocation, as reported back to the model.

    Attributes:
        call_id: Matches the originating :class:`ToolCallStart`.
        output: JSON-serialisable value returned by the tool.
    """

    call_id: str
    output: Any


@dataclass(frozen=True, slots=True)
class Finish:
    """Terminal event of a stream.

    Attributes:
        reason: Vendor-normalised reason the stream ended
            (``"stop"``, ``"length"``, ``"tool_use"``, ...).
        usage: Token accounting for the request, or ``None`` when
            the provider did not report it.
    """

    reason: str
    usage: TokenUsage | None = None


LLMChunk = TextChunk | ToolCallStart | ToolCallEnd | ToolResult | Finish
