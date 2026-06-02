"""Input contract for :class:`phronesis.context.ContextBuilder` implementations.

:class:`BuildInput` is a frozen, slotted dataclass carrying everything a
builder needs to produce the next message list: the system prompt, the
accumulated history, an optional new user input for the current
iteration, and a reference to the :class:`LLMProvider` (used by builders
that need to query model metadata or perform secondary LLM calls).

The dataclass is intentionally extensible: future components such as
:class:`MemoryStore` or :class:`Policy` will be added as optional fields
without breaking existing builders.
"""

from __future__ import annotations

from dataclasses import dataclass

from phronesis.core.messages import Message
from phronesis.providers.protocol import LLMProvider


@dataclass(frozen=True, slots=True)
class BuildInput:
    """Frozen input passed to :meth:`ContextBuilder.build`.

    Attributes:
        system_prompt: System instructions of the owning agent. May be
            an empty string.
        history: Accumulated conversation history as an immutable
            tuple. Empty on the first iteration.
        new_input: Optional fresh user message to be appended in this
            iteration. ``None`` when the loop is between turns and only
            tool results are pending.
        provider: The :class:`LLMProvider` driving the run. Builders
            that estimate tokens or perform secondary LLM calls use
            this reference; trivial builders may ignore it.
    """

    system_prompt: str
    history: tuple[Message, ...]
    new_input: Message | None
    provider: LLMProvider
