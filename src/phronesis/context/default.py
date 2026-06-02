"""Trivial :class:`ContextBuilder` that returns ``[system, *history]``.

:class:`DefaultContextBuilder` performs no token estimation, no
truncation and no compaction. When the resulting message list outgrows
the provider's context window, the provider call fails and the agent
loop surfaces the error as
:class:`phronesis.agents.errors.AgentExecutionError`.

The builder is stateless and safe to share across runs; the framework
exposes a module-level singleton through
:mod:`phronesis.agents.decorator`.
"""

from __future__ import annotations

import asyncio

from phronesis.context.input import BuildInput
from phronesis.core.messages import Message, SystemMessage, TextBlock


class DefaultContextBuilder:
    """Pass-through builder: ``system + history + new_input``."""

    async def build(self, input: BuildInput) -> list[Message]:
        """Return the system prompt, full history and optional new input.

        The system prompt is emitted as a :class:`SystemMessage` only
        when ``input.system_prompt`` is truthy and the history does
        not already start with one. The history is copied positionally
        so callers may mutate the returned list without affecting the
        immutable tuple stored in the run.

        Args:
            input: Current :class:`BuildInput`.

        Returns:
            A list of :class:`Message` ready for the provider.
        """
        messages: list[Message] = []
        history_starts_with_system = bool(input.history) and isinstance(
            input.history[0], SystemMessage
        )

        if input.system_prompt and not history_starts_with_system:
            messages.append(SystemMessage(content=(TextBlock(text=input.system_prompt),)))

        messages.extend(input.history)

        if input.new_input is not None:
            messages.append(input.new_input)

        await asyncio.sleep(0)

        return messages
