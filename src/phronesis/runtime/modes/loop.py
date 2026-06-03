"""Loop: repeat a node while a predicate returns truthy."""

from __future__ import annotations

import inspect
from collections.abc import Awaitable, Callable
from dataclasses import dataclass
from typing import Any

from phronesis.runtime.context import ExecutionContext
from phronesis.runtime.errors import CancelledError, ExecutionFailedError, LoopExhaustedError
from phronesis.runtime.obs import RUNTIME_ITERATION, runtime_span
from phronesis.runtime.outcome import RunOutcome
from phronesis.runtime.protocol import Executable


@dataclass(frozen=True, slots=True)
class Loop:
    """Repeat ``body`` while ``until(output)`` is truthy.

    Attributes:
        body: Node invoked each iteration; output threads to the next.
        until: Predicate evaluated after every body call. ``True`` keeps
            the loop going; ``False`` stops it with the last output.
        max_iterations: Hard cap; reaching it raises
            :class:`LoopExhaustedError`.
    """

    body: Executable
    until: Callable[[Any], Awaitable[bool] | bool]
    max_iterations: int = 10

    async def __call__(self, ctx: ExecutionContext, input: Any) -> RunOutcome:
        async with runtime_span("loop", run_id=ctx.run_id.canonical):
            children: list[RunOutcome] = []
            current: Any = input

            for iteration in range(1, self.max_iterations + 1):
                if ctx.is_cancelled():
                    return RunOutcome.fail(
                        error=CancelledError("loop cancelled"),
                        children=tuple(children),
                    ).merge_children()

                outcome = await self.body(
                    ctx.child(metadata={RUNTIME_ITERATION: iteration}),
                    current,
                )
                children.append(outcome)

                if not outcome.success:
                    return RunOutcome.fail(
                        error=outcome.error or ExecutionFailedError("loop body failed"),
                        output=outcome.output,
                        children=tuple(children),
                        metadata={RUNTIME_ITERATION: iteration},
                    ).merge_children()

                current = outcome.output
                verdict = self.until(current)

                if inspect.isawaitable(verdict):
                    verdict = await verdict

                if not verdict:
                    return RunOutcome.ok(
                        output=current,
                        children=tuple(children),
                        metadata={RUNTIME_ITERATION: iteration},
                    ).merge_children()

            return RunOutcome.fail(
                error=LoopExhaustedError(
                    f"loop reached max_iterations={self.max_iterations}",
                    details={"max_iterations": self.max_iterations},
                ),
                output=current,
                children=tuple(children),
                metadata={RUNTIME_ITERATION: self.max_iterations},
            ).merge_children()
