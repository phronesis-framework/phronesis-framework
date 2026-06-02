"""Sequential composition of :class:`ContextBuilder` instances.

A :class:`ChainedContextBuilder` runs each child builder in
declaration order, feeding the output of one as the ``history`` of
the next. This makes it possible to compose orthogonal concerns -
e.g. compact long histories, then inject RAG snippets, then attach a
prompt-cache marker - without writing a monolithic builder.

Chaining semantics:

* Only the **first** child sees ``input.new_input``. Subsequent
  builders receive ``new_input=None`` because the input has already
  been appended to the running history by the first builder.
* Each child receives ``input.system_prompt`` unchanged. Any
  :class:`SystemMessage` produced by the previous step is stripped
  from the intermediate history so the next builder can prepend its
  own system message without duplicating.
* ``input.provider`` is forwarded verbatim.
"""

from __future__ import annotations

from collections.abc import Sequence

from phronesis.context.input import BuildInput
from phronesis.context.protocol import ContextBuilder
from phronesis.core.messages import Message, SystemMessage


class ChainedContextBuilder:
    """A :class:`ContextBuilder` that composes a pipeline of builders.

    Construct directly or via the :func:`chain` factory::

        builder = chain(CompactingContextBuilder(), MyRAGBuilder())

    Attributes:
        builders: The ordered tuple of child :class:`ContextBuilder`
            instances.
    """

    __slots__ = ("builders",)

    def __init__(self, builders: Sequence[ContextBuilder]) -> None:
        """Bind ``builders`` into a sequential chain.

        Args:
            builders: Non-empty sequence of :class:`ContextBuilder`
                instances. Order matters - the first builder consumes
                ``new_input``.

        Raises:
            ValueError: if ``builders`` is empty.
        """
        materialised = tuple(builders)

        if not materialised:
            raise ValueError("ChainedContextBuilder requires at least one builder.")

        self.builders: tuple[ContextBuilder, ...] = materialised

    async def build(self, input: BuildInput) -> list[Message]:
        """Run every child builder in turn and return the final list.

        Args:
            input: The :class:`BuildInput` for the current iteration.

        Returns:
            The output of the last builder in the chain.
        """
        messages = await self.builders[0].build(input)

        for builder in self.builders[1:]:
            history = tuple(m for m in messages if not isinstance(m, SystemMessage))
            next_input = BuildInput(
                system_prompt=input.system_prompt,
                history=history,
                new_input=None,
                provider=input.provider,
            )
            messages = await builder.build(next_input)

        return messages


def chain(*builders: ContextBuilder) -> ChainedContextBuilder:
    """Build a :class:`ChainedContextBuilder` from a varargs list.

    Args:
        *builders: Two or more :class:`ContextBuilder` instances to
            compose. A single builder is accepted but produces a
            trivial chain.

    Returns:
        A :class:`ChainedContextBuilder` that runs ``builders`` in
        order.

    Raises:
        ValueError: if ``builders`` is empty.
    """
    return ChainedContextBuilder(builders)
