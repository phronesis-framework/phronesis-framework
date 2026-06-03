"""Plan-and-execute: a planner emits steps, an executor runs them."""

from __future__ import annotations

from collections.abc import Callable, Mapping
from collections.abc import Sequence as SeqAlias
from dataclasses import dataclass, field
from typing import Any

from phronesis.runtime.context import ExecutionContext
from phronesis.runtime.obs import RUNTIME_ITERATION, runtime_span
from phronesis.runtime.outcome import RunOutcome
from phronesis.runtime.protocol import Executable


def default_step_extractor(output: Any) -> SeqAlias[Any]:
    """Return ``output["steps"]``, ``output.steps`` or ``output`` itself."""
    if isinstance(output, Mapping) and "steps" in output:
        return list(output["steps"])

    steps = getattr(output, "steps", None)

    if steps is not None:
        return list(steps)

    if isinstance(output, (list, tuple)):
        return list(output)

    return [output]


@dataclass(frozen=True, slots=True)
class PlanAndExecute:
    """Run the planner once, then the executor on every emitted step.

    Attributes:
        planner: Executable producing a list of steps from the input.
        executor: Executable invoked once per step.
        step_extractor: Callable extracting the step list from the
            planner's output. Defaults to :func:`default_step_extractor`.
    """

    planner: Executable
    executor: Executable
    step_extractor: Callable[[Any], SeqAlias[Any]] = field(default=default_step_extractor)

    async def __call__(self, ctx: ExecutionContext, input: Any) -> RunOutcome:
        async with runtime_span("plan_and_execute", run_id=ctx.run_id.canonical):
            plan_outcome = await self.planner(ctx.child(), input)
            children: list[RunOutcome] = [plan_outcome]

            if not plan_outcome.success:
                return RunOutcome.fail(
                    error=plan_outcome.error or Exception("planner failed"),
                    children=tuple(children),
                ).merge_children()

            steps = list(self.step_extractor(plan_outcome.output))
            results: list[Any] = []

            for idx, step in enumerate(steps, start=1):
                step_outcome = await self.executor(
                    ctx.child(metadata={RUNTIME_ITERATION: idx}),
                    step,
                )
                children.append(step_outcome)

                if not step_outcome.success:
                    return RunOutcome.fail(
                        error=step_outcome.error or Exception(f"step {idx} failed"),
                        children=tuple(children),
                    ).merge_children()

                results.append(step_outcome.output)

            return RunOutcome.ok(
                output=tuple(results),
                children=tuple(children),
            ).merge_children()
