"""Fallback: try ``primary``, then each fallback until one succeeds."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from phronesis.runtime.context import ExecutionContext
from phronesis.runtime.errors import ExecutionFailedError
from phronesis.runtime.obs import runtime_span
from phronesis.runtime.outcome import RunOutcome
from phronesis.runtime.protocol import Executable


@dataclass(frozen=True, slots=True)
class Fallback:
    """Try ``primary`` then each entry in ``fallbacks`` until one succeeds.

    Attributes:
        primary: First executable tried.
        fallbacks: Tuple of executables tried in order on failure.
    """

    primary: Executable
    fallbacks: tuple[Executable, ...]

    async def __call__(self, ctx: ExecutionContext, input: Any) -> RunOutcome:
        async with runtime_span("fallback", run_id=ctx.run_id.canonical):
            attempts: list[RunOutcome] = []

            for node in (self.primary, *self.fallbacks):
                try:
                    outcome = await node(ctx.child(), input)
                except Exception as exc:
                    outcome = RunOutcome.fail(error=exc)

                attempts.append(outcome)

                if outcome.success:
                    return RunOutcome.ok(
                        output=outcome.output,
                        children=tuple(attempts),
                    ).merge_children()

            last = attempts[-1]

            return RunOutcome.fail(
                error=last.error or ExecutionFailedError("all fallbacks failed"),
                children=tuple(attempts),
            ).merge_children()
