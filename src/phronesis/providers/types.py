"""Request/response types exchanged with a provider.

Frozen, slotted dataclasses in the same style as :mod:`phronesis.tools`.
These types are framework-internal data plumbing; validation of user
input happens at the boundaries (factory functions, HTTP I/O), not on
every transformation.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import StrEnum
from typing import Any

from phronesis.providers.usage import TokenUsage
from phronesis.tools import ToolSpec


class Role(StrEnum):
    """Conversational role of a message."""

    SYSTEM = "system"
    USER = "user"
    ASSISTANT = "assistant"
    TOOL = "tool"


@dataclass(frozen=True, slots=True)
class ToolCall:
    """A tool invocation requested by the assistant."""

    call_id: str
    tool_name: str
    arguments: dict[str, Any]


@dataclass(frozen=True, slots=True)
class Message:
    """A single message in the conversation.

    Attributes:
        role: Conversational role.
        content: Free-form text content. Empty for assistant messages
            that contain only tool calls, and for tool messages whose
            payload lives in ``tool_output``.
        tool_calls: Tool invocations attached to an assistant message.
        tool_call_id: For ``Role.TOOL`` messages, the id of the
            originating tool call.
        tool_output: For ``Role.TOOL`` messages, the result the tool
            produced.
    """

    role: Role
    content: str = ""
    tool_calls: tuple[ToolCall, ...] = ()
    tool_call_id: str | None = None
    tool_output: Any = None


@dataclass(frozen=True, slots=True)
class LLMRequest:
    """A request to a provider's ``complete``/``stream`` operation."""

    model: str
    messages: tuple[Message, ...]
    tools: tuple[ToolSpec, ...] = ()
    system: str | None = None
    temperature: float | None = None
    max_tokens: int | None = None
    metadata: dict[str, Any] = field(default_factory=dict)


@dataclass(frozen=True, slots=True)
class LLMResponse:
    """A non-streaming response from a provider."""

    text: str = ""
    tool_calls: tuple[ToolCall, ...] = ()
    finish_reason: str = ""
    usage: TokenUsage | None = None
