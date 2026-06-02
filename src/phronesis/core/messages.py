"""Domain message types for agent conversations.

A message is one of :class:`SystemMessage`, :class:`UserMessage`,
:class:`AssistantMessage` or :class:`ToolMessage`. Every message
carries a tuple of :class:`ContentBlock` so multimodal content
(text, tool calls, tool results) is expressible without per-role
attribute soup.

These types model the **agent's** view of a conversation. The
flatter ``phronesis.providers.types.Message`` is provider-side
plumbing; the loop is responsible for translating between the two
when calling a provider.
"""

from __future__ import annotations

import uuid
from collections.abc import Mapping
from dataclasses import dataclass, field
from datetime import UTC, datetime
from types import MappingProxyType
from typing import Any, Final, Literal

from phronesis._internal.ids.generator import IdGenerator
from phronesis._internal.ids.id import Id

_EMPTY_ARGS: Final[Mapping[str, Any]] = MappingProxyType({})


class MessageId(Id):
    """Stable identifier for a single :class:`Message` instance.

    Subclass of :class:`phronesis._internal.ids.id.Id` with the short
    prefix ``"MID"``. Useful for replay, tracing and observability -
    every message produced by the framework carries one.
    """

    prefix = "MID"


message_id_generator: IdGenerator[MessageId] = IdGenerator(MessageId)
"""Process-wide :class:`IdGenerator` bound to :class:`MessageId`."""


def _new_message_id() -> MessageId:
    return message_id_generator.from_canonical(
        f"phronesis.core.messages.m{uuid.uuid4().hex[:12]}",
    )


def _now() -> datetime:
    return datetime.now(UTC)


@dataclass(frozen=True, slots=True)
class TextBlock:
    """Plain text content.

    Attributes:
        text: The block's textual content.
        cache: Marks this block as the end of a cacheable prefix.
            Providers that support prompt caching (e.g. Anthropic)
            translate the flag into their native cache hint; providers
            that don't ignore it. The flag is advisory - set it on the
            last block of a stable prefix (system prompt, tool
            definitions, long static context) to opt into caching.
    """

    text: str
    cache: bool = False


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


@dataclass(frozen=True, slots=True)
class CompactionSummaryBlock:
    """Compacted summary of a span of prior conversation.

    Produced by :class:`phronesis.context.CompactingContextBuilder`
    when the rolling history outgrows the model's context window.
    The summary text replaces the compacted slice on subsequent
    iterations so the model still sees the gist without paying for
    every original token.

    Attributes:
        text: Natural-language summary of the compacted messages.
        original_message_count: Number of original messages this
            block stands in for. Useful for observability and to
            short-circuit re-compaction of an already-summarised
            prefix.
    """

    text: str
    original_message_count: int


@dataclass(frozen=True, slots=True)
class ImageBlock:
    """Image content carried in a message.

    Attributes:
        data: Either a fully qualified URL or a base64-encoded payload,
            disambiguated by :attr:`source_type`.
        media_type: IANA media type of the image. Defaults to
            ``"image/png"``.
        source_type: ``"url"`` when :attr:`data` is a URL, ``"base64"``
            when it is an inline payload. Defaults to ``"url"``.

    Providers that advertise :attr:`ProviderFeature.VISION` translate
    the block into their native shape; providers that do not silently
    drop it.
    """

    data: str
    media_type: str = "image/png"
    source_type: Literal["url", "base64"] = "url"


@dataclass(frozen=True, slots=True)
class DocumentBlock:
    """Document content carried in a message.

    Attributes:
        data: Either a fully qualified URL or a base64-encoded payload,
            disambiguated by :attr:`source_type`.
        media_type: IANA media type. Defaults to ``"application/pdf"``.
        source_type: ``"url"`` when :attr:`data` is a URL, ``"base64"``
            when it is an inline payload. Defaults to ``"url"``.

    Providers that advertise :attr:`ProviderFeature.DOCUMENTS`
    translate the block into their native shape; providers that do
    not silently drop it.
    """

    data: str
    media_type: str = "application/pdf"
    source_type: Literal["url", "base64"] = "url"


ContentBlock = (
    TextBlock | ToolUseBlock | ToolResultBlock | CompactionSummaryBlock | ImageBlock | DocumentBlock
)
"""Union of the MVP content block types."""


@dataclass(frozen=True, slots=True)
class SystemMessage:
    """System prompt or directive (typically a single :class:`TextBlock`).

    Attributes:
        content: Tuple of :class:`ContentBlock` instances.
        id: Auto-generated :class:`MessageId`. Excluded from equality
            comparison and :func:`repr` so existing tests stay stable.
        created_at: Timezone-aware UTC creation timestamp.
    """

    content: tuple[ContentBlock, ...]
    id: MessageId = field(default_factory=_new_message_id, compare=False, repr=False)
    created_at: datetime = field(default_factory=_now, compare=False, repr=False)


@dataclass(frozen=True, slots=True)
class UserMessage:
    """A message authored by the human or upstream caller.

    Attributes:
        content: Tuple of :class:`ContentBlock` instances.
        id: Auto-generated :class:`MessageId`. Excluded from equality
            comparison and :func:`repr`.
        created_at: Timezone-aware UTC creation timestamp.
    """

    content: tuple[ContentBlock, ...]
    id: MessageId = field(default_factory=_new_message_id, compare=False, repr=False)
    created_at: datetime = field(default_factory=_now, compare=False, repr=False)


@dataclass(frozen=True, slots=True)
class AssistantMessage:
    """A message produced by the model.

    May contain a mix of :class:`TextBlock` and :class:`ToolUseBlock`.

    Attributes:
        content: Tuple of :class:`ContentBlock` instances.
        id: Auto-generated :class:`MessageId`. Excluded from equality
            comparison and :func:`repr`.
        created_at: Timezone-aware UTC creation timestamp.
    """

    content: tuple[ContentBlock, ...]
    id: MessageId = field(default_factory=_new_message_id, compare=False, repr=False)
    created_at: datetime = field(default_factory=_now, compare=False, repr=False)


@dataclass(frozen=True, slots=True)
class ToolMessage:
    """Results of tool executions returned to the model.

    Carries one or more :class:`ToolResultBlock`.

    Attributes:
        content: Tuple of :class:`ContentBlock` instances.
        id: Auto-generated :class:`MessageId`. Excluded from equality
            comparison and :func:`repr`.
        created_at: Timezone-aware UTC creation timestamp.
    """

    content: tuple[ContentBlock, ...]
    id: MessageId = field(default_factory=_new_message_id, compare=False, repr=False)
    created_at: datetime = field(default_factory=_now, compare=False, repr=False)


Message = SystemMessage | UserMessage | AssistantMessage | ToolMessage
"""Union of the four conversational roles."""
