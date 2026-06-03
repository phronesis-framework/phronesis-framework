"""Reflexion: actor produces; critic evaluates; actor retries with feedback."""

from __future__ import annotations

import inspect
from collections.abc import Awaitable, Callable
from dataclasses import dataclass
from typing import Any

from phronesis.runtime.context import ExecutionContext
from phronesis.runtime.errors import ValidationFailedError
from phronesis.runtime.modes.validation import ValidationResult
from phronesis.runtime.obs import RUNTIME_ITERATION, runtime_span
from phronesis.runtime.outcome import RunOutcome
from phronesis.runtime.protocol import Executable


@dataclass(frozen=True, slots=True)
class Reflexion:
    """Actor + critic loop.

    The critic returns either a :class:`ValidationResult` or any callable
    output - any callable yielding a value with ``.valid`` and
    ``.feedback`` attributes works.

    Attributes:
        actor: Executable producing the candidate output.
        critic: Sync/async callable, or executable, evaluating the
            candidate.
        max_iterations: Hard cap on actor invocations.
    """

    actor: Executable
    critic: Executable | Callable[[Any], Awaitable[ValidationResult] | ValidationResult]
    max_iterations: int = 3

    async def __call__(self, ctx: ExecutionContext, input: Any) -> RunOutcome:
        async with runtime_span("reflexion", run_id=ctx.run_id.canonical):
            children: list[RunOutcome] = []
            last_feedback: str = ""
            last_output: Any = None

            for attempt in range(1, self.max_iterations + 1):
                child_ctx = ctx.child(
                    metadata={
                        RUNTIME_ITERATION: attempt,
                        "runtime.reflexion.feedback": last_feedback,
                    }
                )
                actor_outcome = await self.actor(child_ctx, input)
                children.append(actor_outcome)

                if not actor_outcome.success:
                    return RunOutcome.fail(
                        error=actor_outcome.error or Exception("actor failed"),
                        children=tuple(children),
                    ).merge_children()

                last_output = actor_outcome.output
                verdict = await _evaluate_critic(self.critic, ctx, actor_outcome.output)

                if isinstance(verdict, RunOutcome):
                    children.append(verdict)

                    if not verdict.success:
                        return RunOutcome.fail(
                            error=verdict.error or Exception("critic failed"),
                            children=tuple(children),
                        ).merge_children()

                    result = verdict.output
                else:
                    result = verdict

                if not isinstance(result, ValidationResult):
                    return RunOutcome.fail(
                        error=TypeError("reflexion critic must produce a ValidationResult"),
                        children=tuple(children),
                    ).merge_children()

                if result.valid:
                    return RunOutcome.ok(
                        output=last_output,
                        children=tuple(children),
                        metadata={RUNTIME_ITERATION: attempt},
                    ).merge_children()

                last_feedback = result.feedback

            return RunOutcome.fail(
                error=ValidationFailedError(
                    f"reflexion exhausted {self.max_iterations} attempts",
                    details={"feedback": last_feedback},
                ),
                output=last_output,
                children=tuple(children),
            ).merge_children()


async def _evaluate_critic(
    critic: Any,
    ctx: ExecutionContext,
    candidate: Any,
) -> Any:
    """Run ``critic`` whether it is an executable or a plain callable."""
    from phronesis.runtime.protocol import Executable as _Exec

    if isinstance(critic, _Exec) and not (inspect.isfunction(critic) or inspect.ismethod(critic)):
        return await critic(ctx.child(), candidate)

    verdict = critic(candidate)

    if inspect.isawaitable(verdict):
        verdict = await verdict

    return verdict
