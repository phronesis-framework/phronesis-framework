"""Structural contract every context builder satisfies.

:class:`ContextBuilder` is a :class:`typing.Protocol` so users may
plug in their own implementations (e.g. RAG, custom compaction,
memory retrieval) without inheriting from a base class. The framework
ships two reference implementations:
:class:`phronesis.context.DefaultContextBuilder` and
:class:`phronesis.context.CompactingContextBuilder`.

The protocol is :func:`runtime_checkable` so callers can validate
custom builders with :func:`isinstance` at registration time.
"""

from __future__ import annotations

from typing import Protocol, runtime_checkable

from phronesis.context.input import BuildInput
from phronesis.core.messages import Message


@runtime_checkable
class ContextBuilder(Protocol):
    """Stateless transformer from run state to provider-ready messages.

    Implementations must be safe to share across concurrent runs: any
    mutable state belongs in the :class:`BuildInput` (i.e. in the
    history) rather than on the instance.
    """

    async def build(self, input: BuildInput) -> list[Message]:
        """Return the list of messages to send on the next iteration.

        Args:
            input: The frozen :class:`BuildInput` describing the
                current run state.

        Returns:
            A list of :class:`Message` ready for translation into the
            provider's wire format. Typically starts with a
            :class:`SystemMessage` derived from
            ``input.system_prompt`` and ends with ``input.new_input``
            when present.
        """
        ...
