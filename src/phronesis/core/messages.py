"""Domain message types for agent conversations.

See ``docs/AGENTS-DECISIONS.md`` (D-08): a message is one of
:class:`SystemMessage`, :class:`UserMessage`, :class:`AssistantMessage`
or :class:`ToolMessage`. Every message carries a tuple of
:class:`ContentBlock` so multimodal content (text, tool calls, tool
results) is expressible without per-role attribute soup.

These types model the **agent's** view of a conversation. The flatter
``phronesis.providers.types.Message`` is provider-side plumbing; the
loop is responsible for translating between the two when calling a
provider.
"""

from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass, field
from types import MappingProxyType
from typing import Any, Final

_EMPTY_ARGS: Final[Mapping[str, Any]] = MappingProxyType({})


@dataclass(frozen=True, slots=True)
class TextBlock:
    """Plain text content."""

    text: str


@dataclass(frozen=True, slots=True)
class ToolUseBlock:
    """An assistant's request to invoke a tool.

    Attributes:
        tool_call_id: Provider-issued id linking this request to its
            future :class:`ToolResultBlock`.
        tool_name: LLM-facing tool name (matches ``ToolSpec.name``).
        args: Arguments the model asked to pass to the tool.
    """

    tool_call_id: str
    tool_name: str
    args: Mapping[str, Any] = field(default_factory=lambda: _EMPTY_ARGS)

    def __post_init__(self) -> None:
        if not isinstance(self.args, MappingProxyType):
            object.__setattr__(self, "args", MappingProxyType(dict(self.args)))


@dataclass(frozen=True, slots=True)
class ToolResultBlock:
    """The result of executing a tool call.

    Attributes:
        tool_call_id: Id of the originating :class:`ToolUseBlock`.
        output: Whatever the tool produced. May be any
            JSON-serializable value, or an error payload when
            ``is_error`` is true.
        is_error: ``True`` when the tool raised a serialized
            :class:`phronesis.tools.errors.ToolError`.
    """

    tool_call_id: str
    output: Any
    is_error: bool = False


ContentBlock = TextBlock | ToolUseBlock | ToolResultBlock
"""Union of the MVP content block types."""


@dataclass(frozen=True, slots=True)
class SystemMessage:
    """System prompt or directive (typically a single :class:`TextBlock`)."""

    content: tuple[ContentBlock, ...]


@dataclass(frozen=True, slots=True)
class UserMessage:
    """A message authored by the human or upstream caller."""

    content: tuple[ContentBlock, ...]


@dataclass(frozen=True, slots=True)
class AssistantMessage:
    """A message produced by the model.

    May contain a mix of :class:`TextBlock` and :class:`ToolUseBlock`.
    """

    content: tuple[ContentBlock, ...]


@dataclass(frozen=True, slots=True)
class ToolMessage:
    """Results of tool executions returned to the model.

    Carries one or more :class:`ToolResultBlock`.
    """

    content: tuple[ContentBlock, ...]


Message = SystemMessage | UserMessage | AssistantMessage | ToolMessage
"""Union of the four conversational roles."""
