"""Validation: run a node and retry with feedback if the validator rejects."""

from __future__ import annotations

import inspect
from collections.abc import Awaitable, Callable
from dataclasses import dataclass
from typing import Any

from phronesis.runtime.context import ExecutionContext
from phronesis.runtime.errors import ValidationFailedError
from phronesis.runtime.obs import RUNTIME_ITERATION, runtime_span
from phronesis.runtime.outcome import RunOutcome
from phronesis.runtime.protocol import Executable


@dataclass(frozen=True, slots=True)
class ValidationResult:
    """Verdict returned by a :class:`Validation` validator.

    Attributes:
        valid: ``True`` accepts the output and ends the loop.
        feedback: Human-readable rationale for the next attempt.
    """

    valid: bool
    feedback: str = ""


@dataclass(frozen=True, slots=True)
class Validation:
    """Run ``node``; if the validator rejects, retry up to ``max_attempts``.

    The feedback from the validator is exposed to the next attempt via the
    derived context's metadata under ``runtime.validation.feedback``.

    Attributes:
        node: Executable to invoke.
        validator: Callable producing a :class:`ValidationResult`.
        max_attempts: Hard cap on attempts.
    """

    node: Executable
    validator: Callable[[Any], Awaitable[ValidationResult] | ValidationResult]
    max_attempts: int = 3

    async def __call__(self, ctx: ExecutionContext, input: Any) -> RunOutcome:
        async with runtime_span("validation", run_id=ctx.run_id.canonical):
            attempts: list[RunOutcome] = []
            last_feedback: str = ""

            for attempt in range(1, self.max_attempts + 1):
                child_ctx = ctx.child(
                    metadata={
                        RUNTIME_ITERATION: attempt,
                        "runtime.validation.feedback": last_feedback,
                    }
                )
                outcome = await self.node(child_ctx, input)
                attempts.append(outcome)

                if not outcome.success:
                    return RunOutcome.fail(
                        error=outcome.error or ValidationFailedError("node failed"),
                        children=tuple(attempts),
                    ).merge_children()

                verdict = self.validator(outcome.output)

                if inspect.isawaitable(verdict):
                    verdict = await verdict

                if verdict.valid:
                    return RunOutcome.ok(
                        output=outcome.output,
                        children=tuple(attempts),
                        metadata={RUNTIME_ITERATION: attempt},
                    ).merge_children()

                last_feedback = verdict.feedback

            return RunOutcome.fail(
                error=ValidationFailedError(
                    f"validator rejected {self.max_attempts} attempts",
                    details={"feedback": last_feedback},
                ),
                children=tuple(attempts),
            ).merge_children()
