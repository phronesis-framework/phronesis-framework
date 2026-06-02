"""Conditional branching on a (possibly async) predicate."""

from __future__ import annotations

import inspect
from collections.abc import Awaitable, Callable
from dataclasses import dataclass
from typing import Any

from phronesis.runtime.context import ExecutionContext
from phronesis.runtime.obs import runtime_span
from phronesis.runtime.outcome import RunOutcome
from phronesis.runtime.protocol import Executable


@dataclass(frozen=True, slots=True)
class Conditional:
    """Run ``on_true`` or ``on_false`` based on ``predicate(input)``.

    Attributes:
        predicate: Sync or async callable receiving the input and
            returning a truthy/falsy verdict.
        on_true: Node executed when the predicate is truthy.
        on_false: Node executed when the predicate is falsy.
    """

    predicate: Callable[[Any], Awaitable[bool] | bool]
    on_true: Executable
    on_false: Executable

    async def __call__(self, ctx: ExecutionContext, input: Any) -> RunOutcome:
        async with runtime_span("conditional", run_id=ctx.run_id.canonical):
            verdict = self.predicate(input)

            if inspect.isawaitable(verdict):
                verdict = await verdict

            branch = self.on_true if verdict else self.on_false
            outcome = await branch(ctx.child(), input)

            return outcome
