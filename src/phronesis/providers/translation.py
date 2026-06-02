"""Translate framework messages into provider wire messages.

Bridges :class:`phronesis.core.messages.Message` (the agent-side
view, with typed :class:`ContentBlock` tuples) and
:class:`phronesis.providers.types.Message` (the flatter wire shape
each provider adapter consumes).

This module is provider-neutral: it lives under ``phronesis.providers``
so providers can import it without depending on ``phronesis.agents``,
breaking what would otherwise be a layering cycle.
"""

from __future__ import annotations

from collections.abc import Sequence

from phronesis.core.messages import (
    AssistantMessage,
    CompactionSummaryBlock,
    ContentBlock,
    DocumentBlock,
    ImageBlock,
    Message,
    SystemMessage,
    TextBlock,
    ToolResultBlock,
    ToolUseBlock,
    UserMessage,
)
from phronesis.providers.types import MediaRef
from phronesis.providers.types import Message as ProviderMessage
from phronesis.providers.types import Role as ProviderRole
from phronesis.providers.types import ToolCall as ProviderToolCall


def translate_history(history: Sequence[Message]) -> tuple[ProviderMessage, ...]:
    """Translate ``history`` into a tuple of provider messages.

    Each domain message expands into one or more provider messages:

    * :class:`SystemMessage`, :class:`UserMessage` and
      :class:`AssistantMessage` become a single provider message
      with their text concatenated.
    * :class:`ToolMessage` expands into one provider message per
      :class:`ToolResultBlock` carried in its content.

    The :attr:`TextBlock.cache` flag is propagated to the resulting
    provider message's ``cache`` field when any text block in the
    domain message is cached.

    Args:
        history: Sequence of framework-side messages.

    Returns:
        Tuple of provider messages ready for an
        :class:`phronesis.providers.types.LLMRequest`.
    """
    translated: list[ProviderMessage] = []

    for message in history:
        translated.extend(_translate_one(message))

    return tuple(translated)


def _translate_one(message: Message) -> list[ProviderMessage]:
    cache_hint = _has_cache_hint(message.content)
    media = _collect_media(message.content)

    if isinstance(message, SystemMessage):
        return [
            ProviderMessage(
                role=ProviderRole.SYSTEM,
                content=_concat_text(message.content),
                cache=cache_hint,
                media=media,
            ),
        ]

    if isinstance(message, UserMessage):
        return [
            ProviderMessage(
                role=ProviderRole.USER,
                content=_concat_text(message.content),
                cache=cache_hint,
                media=media,
            ),
        ]

    if isinstance(message, AssistantMessage):
        tool_calls = tuple(
            ProviderToolCall(
                call_id=block.tool_call_id,
                tool_name=block.tool_name,
                arguments=dict(block.args),
            )
            for block in message.content
            if isinstance(block, ToolUseBlock)
        )

        return [
            ProviderMessage(
                role=ProviderRole.ASSISTANT,
                content=_concat_text(message.content),
                tool_calls=tool_calls,
                cache=cache_hint,
                media=media,
            ),
        ]

    # ToolMessage: one provider message per ToolResultBlock.
    return [
        ProviderMessage(
            role=ProviderRole.TOOL,
            content="",
            tool_call_id=block.tool_call_id,
            tool_output=block.output,
        )
        for block in message.content
        if isinstance(block, ToolResultBlock)
    ]


def _concat_text(blocks: tuple[ContentBlock, ...]) -> str:
    parts: list[str] = []

    for block in blocks:
        if isinstance(block, TextBlock):
            parts.append(block.text)
            continue

        if isinstance(block, CompactionSummaryBlock):
            parts.append(block.text)

    return "".join(parts)


def _has_cache_hint(blocks: tuple[ContentBlock, ...]) -> bool:
    return any(isinstance(block, TextBlock) and block.cache for block in blocks)


def _collect_media(blocks: tuple[ContentBlock, ...]) -> tuple[MediaRef, ...]:
    refs: list[MediaRef] = []

    for block in blocks:
        if isinstance(block, ImageBlock):
            refs.append(
                MediaRef(
                    kind="image",
                    data=block.data,
                    media_type=block.media_type,
                    source_type=block.source_type,
                ),
            )
            continue

        if isinstance(block, DocumentBlock):
            refs.append(
                MediaRef(
                    kind="document",
                    data=block.data,
                    media_type=block.media_type,
                    source_type=block.source_type,
                ),
            )

    return tuple(refs)
