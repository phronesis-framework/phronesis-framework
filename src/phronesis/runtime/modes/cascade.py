"""Cascade: try nodes in order until ``acceptance(output)`` accepts."""

from __future__ import annotations

import inspect
from collections.abc import Awaitable, Callable
from dataclasses import dataclass
from typing import Any

from phronesis.runtime.context import ExecutionContext
from phronesis.runtime.errors import ExecutionFailedError
from phronesis.runtime.obs import runtime_span
from phronesis.runtime.outcome import RunOutcome
from phronesis.runtime.protocol import Executable


@dataclass(frozen=True, slots=True)
class Cascade:
    """Try nodes in order (cheap -> expensive) until ``acceptance`` accepts.

    Attributes:
        nodes: Tuple of executables tried in order.
        acceptance: Predicate evaluated on the produced output. The first
            node whose output is accepted wins.
    """

    nodes: tuple[Executable, ...]
    acceptance: Callable[[Any], Awaitable[bool] | bool]

    async def __call__(self, ctx: ExecutionContext, input: Any) -> RunOutcome:
        async with runtime_span("cascade", run_id=ctx.run_id.canonical):
            attempts: list[RunOutcome] = []

            for node in self.nodes:
                outcome = await node(ctx.child(), input)
                attempts.append(outcome)

                if not outcome.success:
                    continue

                verdict = self.acceptance(outcome.output)

                if inspect.isawaitable(verdict):
                    verdict = await verdict

                if verdict:
                    return RunOutcome.ok(
                        output=outcome.output,
                        children=tuple(attempts),
                    ).merge_children()

            return RunOutcome.fail(
                error=ExecutionFailedError("no cascade node was accepted"),
                children=tuple(attempts),
            ).merge_children()
