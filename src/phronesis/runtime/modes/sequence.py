"""Sequential composition: ``output[n] -> input[n+1]``.

A :class:`Sequence` runs its nodes in order, threading each node's output
as the next node's input. The first failure aborts the chain; remaining
nodes are not invoked. Tokens and cost from every node executed are
folded into the final outcome via :meth:`RunOutcome.merge_children`.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from phronesis.runtime.context import ExecutionContext
from phronesis.runtime.errors import CancelledError, ExecutionFailedError
from phronesis.runtime.obs import runtime_span
from phronesis.runtime.outcome import RunOutcome
from phronesis.runtime.protocol import Executable


@dataclass(frozen=True, slots=True)
class Sequence:
    """Chain nodes; each node's output becomes the next node's input.

    Attributes:
        nodes: Tuple of executables to invoke in order. Empty sequences
            return :meth:`RunOutcome.ok` with the original input.
    """

    nodes: tuple[Executable, ...]

    async def __call__(self, ctx: ExecutionContext, input: Any) -> RunOutcome:
        async with runtime_span("sequence", run_id=ctx.run_id.canonical):
            children: list[RunOutcome] = []
            current: Any = input

            for node in self.nodes:
                if ctx.is_cancelled():
                    return RunOutcome.fail(
                        error=CancelledError("sequence cancelled"),
                        children=tuple(children),
                    ).merge_children()

                child_ctx = ctx.child()
                outcome = await node(child_ctx, current)
                children.append(outcome)

                if not outcome.success:
                    error = outcome.error or ExecutionFailedError("node failed in sequence")

                    return RunOutcome.fail(
                        error=error,
                        output=outcome.output,
                        children=tuple(children),
                    ).merge_children()

                current = outcome.output

            return RunOutcome.ok(output=current, children=tuple(children)).merge_children()
