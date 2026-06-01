"""Compacting :class:`ContextBuilder` for long-running conversations.

:class:`CompactingContextBuilder` estimates the token cost of the
accumulated history and, when it crosses a configurable ratio of the
provider's context window, replaces the older portion with an
LLM-generated summary. The summary is materialised as an
:class:`AssistantMessage` carrying a single
:class:`CompactionSummaryBlock`, so subsequent iterations can detect
already-compacted prefixes and skip re-compaction (statelessness — the
state lives in the history, not on the builder).

Compaction is opt-in: the default agent uses
:class:`DefaultContextBuilder`. Users activate this builder via the
``context_builder`` argument of :func:`phronesis.agents.agent`.

Algorithm (high level):

* Estimate tokens of the current history via
  :meth:`LLMProvider.count_tokens`.
* Compare against ``threshold_ratio * provider.context_window_size()``.
* If below threshold, behave like :class:`DefaultContextBuilder`.
* Otherwise, pick a split point that preserves the last
  ``preserve_recent`` messages without breaking ``tool_use`` /
  ``tool_result`` pairs.
* Call the configured compactor provider (or the run's provider by
  default) with a fixed compaction prompt and the older slice. When a
  prior :class:`CompactionSummaryBlock` exists at the head of the
  history, the compactor receives it as additional context so the new
  output consolidates everything into a single rolling summary
  (incremental compaction).
* Wrap the response in a :class:`CompactionSummaryBlock` and emit
  ``[system, new_summary, *preserved, new_input?]`` — at most one
  summary message survives across iterations.

Failures of the compactor LLM call propagate as :class:`CompactionError`
without fallback — silent degradation would hide budget overruns from
operators.
"""

from __future__ import annotations

from phronesis.context.errors import CompactionError
from phronesis.context.input import BuildInput
from phronesis.core.messages import (
    AssistantMessage,
    CompactionSummaryBlock,
    Message,
    SystemMessage,
    TextBlock,
    ToolMessage,
    ToolResultBlock,
    ToolUseBlock,
    UserMessage,
)
from phronesis.providers.protocol import LLMProvider
from phronesis.providers.types import LLMRequest
from phronesis.providers.types import Message as ProviderMessage
from phronesis.providers.types import Role as ProviderRole

_DEFAULT_THRESHOLD_RATIO = 0.8
_DEFAULT_PRESERVE_RECENT = 6
_DEFAULT_COMPACTION_PROMPT = (
    "You are summarising a long conversation so it fits a smaller context window. "
    "Produce a concise, faithful summary capturing user goals, decisions made, "
    "facts established, tool calls and their outcomes, and any pending follow-ups. "
    "Do not invent details. Reply with the summary text only."
)


class CompactingContextBuilder:
    """Opt-in builder that compacts the older portion of the history.

    Attributes:
        threshold_ratio: Fraction of the provider's context window
            above which compaction kicks in. Defaults to ``0.8``.
        preserve_recent: Number of trailing messages always kept
            verbatim. Defaults to ``6``.
        compactor_provider: Provider used to generate the summary.
            ``None`` means "use the provider of the current run".
        compaction_prompt: Override for the internal compaction
            instructions sent as the system message of the secondary
            LLM call.
    """

    def __init__(
        self,
        *,
        threshold_ratio: float = _DEFAULT_THRESHOLD_RATIO,
        preserve_recent: int = _DEFAULT_PRESERVE_RECENT,
        compactor_provider: LLMProvider | None = None,
        compaction_prompt: str | None = None,
    ) -> None:
        """Initialise the builder with compaction policy parameters.

        Args:
            threshold_ratio: Strictly positive fraction of the context
                window above which compaction triggers.
            preserve_recent: Strictly positive count of recent messages
                always preserved verbatim.
            compactor_provider: Optional override for the LLM used to
                produce the summary. Defaults to the run's provider.
            compaction_prompt: Optional override for the system prompt
                sent to the compactor.
        """
        self._threshold_ratio = threshold_ratio
        self._preserve_recent = preserve_recent
        self._compactor_provider = compactor_provider
        self._compaction_prompt = compaction_prompt or _DEFAULT_COMPACTION_PROMPT

    async def build(self, input: BuildInput) -> list[Message]:
        """Produce the next message list, compacting when necessary.

        Args:
            input: Current :class:`BuildInput`.

        Returns:
            A list of :class:`Message` ready for the provider. May
            include a freshly minted :class:`CompactionSummaryBlock`
            replacing the older portion of ``input.history``.

        Raises:
            CompactionError: when the compactor provider call fails.
        """
        if not self._should_compact(input):
            return _default_messages(input)

        leading_system, tail = _split_leading_system(input.history)
        prior_summary, remaining = _split_existing_summary(tail)
        compactable, preserved = _split_preserving_pairs(remaining, self._preserve_recent)

        if not compactable:
            return _default_messages(input)

        summary_text = await self._summarise(compactable, prior_summary, input)
        rolled_count = _prior_summary_count(prior_summary) + len(compactable)
        summary_message = AssistantMessage(
            content=(
                CompactionSummaryBlock(
                    text=summary_text,
                    original_message_count=rolled_count,
                ),
            ),
        )

        messages: list[Message] = []

        if leading_system:
            messages.extend(leading_system)
        elif input.system_prompt:
            messages.append(SystemMessage(content=(TextBlock(text=input.system_prompt),)))

        messages.append(summary_message)
        messages.extend(preserved)

        if input.new_input is not None:
            messages.append(input.new_input)

        return messages

    def _should_compact(self, input: BuildInput) -> bool:
        if not input.history:
            return False

        limit = input.provider.context_window_size()

        if limit <= 0:
            return False

        used = input.provider.count_tokens(input.history)
        threshold = self._threshold_ratio * limit

        return used >= threshold

    async def _summarise(
        self,
        compactable: tuple[Message, ...],
        prior_summary: tuple[Message, ...],
        input: BuildInput,
    ) -> str:
        provider = self._compactor_provider or input.provider
        compactor_messages = _translate_for_compactor(prior_summary + compactable)
        request = LLMRequest(
            model="",
            messages=compactor_messages,
            tools=(),
            system=self._compaction_prompt,
        )

        try:
            response = await provider.complete(request)
        except Exception as exc:
            raise CompactionError(
                "Compactor provider call failed.",
                details={
                    "provider": type(provider).__name__,
                    "history_size": len(input.history),
                },
            ) from exc

        return response.text


def _default_messages(input: BuildInput) -> list[Message]:
    messages: list[Message] = []
    history_starts_with_system = bool(input.history) and isinstance(input.history[0], SystemMessage)

    if input.system_prompt and not history_starts_with_system:
        messages.append(SystemMessage(content=(TextBlock(text=input.system_prompt),)))

    messages.extend(input.history)

    if input.new_input is not None:
        messages.append(input.new_input)

    return messages


def _split_leading_system(
    history: tuple[Message, ...],
) -> tuple[tuple[Message, ...], tuple[Message, ...]]:
    """Peel any leading :class:`SystemMessage` entries off the history.

    Returns the prefix of contiguous system messages and the remaining
    history. Used to preserve the system prompt verbatim when the loop
    has seeded it into the history tuple.
    """
    cutoff = 0

    for msg in history:
        if isinstance(msg, SystemMessage):
            cutoff += 1
            continue

        break

    return history[:cutoff], history[cutoff:]


def _split_existing_summary(
    history: tuple[Message, ...],
) -> tuple[tuple[Message, ...], tuple[Message, ...]]:
    """Peel any leading already-compacted summary off the history.

    A summary is recognised as an :class:`AssistantMessage` whose only
    content is a :class:`CompactionSummaryBlock`. The function returns
    the prefix of such messages and the remaining history that is still
    candidate for further compaction.
    """
    cutoff = 0

    for msg in history:
        if _is_summary_message(msg):
            cutoff += 1
            continue

        break

    return history[:cutoff], history[cutoff:]


def _is_summary_message(message: Message) -> bool:
    if not isinstance(message, AssistantMessage):
        return False

    return any(isinstance(b, CompactionSummaryBlock) for b in message.content)


def _prior_summary_count(prior_summary: tuple[Message, ...]) -> int:
    """Sum the ``original_message_count`` of any prior summary messages."""
    total = 0

    for msg in prior_summary:
        if not isinstance(msg, AssistantMessage):
            continue

        for block in msg.content:
            if isinstance(block, CompactionSummaryBlock):
                total += block.original_message_count

    return total


def _split_preserving_pairs(
    history: tuple[Message, ...],
    preserve_recent: int,
) -> tuple[tuple[Message, ...], tuple[Message, ...]]:
    """Split ``history`` keeping at least ``preserve_recent`` recent messages.

    The split point is walked backwards as needed so a
    :class:`ToolMessage` never appears in ``preserved`` without the
    :class:`AssistantMessage` that issued the corresponding
    ``tool_use``.
    """
    if preserve_recent <= 0 or not history:
        return history, ()

    split = max(0, len(history) - preserve_recent)
    split = _adjust_split_for_tool_pairs(history, split)

    return history[:split], history[split:]


def _adjust_split_for_tool_pairs(history: tuple[Message, ...], split: int) -> int:
    """Walk ``split`` left so it never lands between tool_use and tool_result."""
    while 0 < split < len(history):
        next_msg = history[split]

        if not isinstance(next_msg, ToolMessage):
            return split

        needed_ids = {b.tool_call_id for b in next_msg.content if isinstance(b, ToolResultBlock)}

        if not needed_ids:
            return split

        if not _has_matching_tool_uses(history[:split], needed_ids):
            return split

        split -= 1

    return split


def _has_matching_tool_uses(prefix: tuple[Message, ...], call_ids: set[str]) -> bool:
    seen: set[str] = set()

    for msg in prefix:
        if not isinstance(msg, AssistantMessage):
            continue

        for block in msg.content:
            if isinstance(block, ToolUseBlock):
                seen.add(block.tool_call_id)

    return call_ids.issubset(seen)


def _translate_for_compactor(messages: tuple[Message, ...]) -> tuple[ProviderMessage, ...]:
    """Render compactable history as plain provider messages.

    The compactor only needs textual context, so tool calls and tool
    results are flattened into their text representation. The summary
    block, if any, is treated as plain text.
    """
    translated: list[ProviderMessage] = []

    for msg in messages:
        role = _role_for(msg)
        content = _flatten_text(msg)
        translated.append(ProviderMessage(role=role, content=content))

    return tuple(translated)


def _role_for(message: Message) -> ProviderRole:
    if isinstance(message, SystemMessage):
        return ProviderRole.SYSTEM

    if isinstance(message, UserMessage):
        return ProviderRole.USER

    if isinstance(message, AssistantMessage):
        return ProviderRole.ASSISTANT

    return ProviderRole.USER


def _flatten_text(message: Message) -> str:
    parts: list[str] = []

    for block in message.content:
        if isinstance(block, TextBlock):
            parts.append(block.text)
            continue

        if isinstance(block, CompactionSummaryBlock):
            parts.append(block.text)
            continue

        if isinstance(block, ToolUseBlock):
            parts.append(f"[tool_use {block.tool_name}({dict(block.args)})]")
            continue

        if isinstance(block, ToolResultBlock):
            parts.append(f"[tool_result {block.output!r}]")

    return "\n".join(p for p in parts if p)
