"""Retry: re-invoke a node with exponential backoff on raised exceptions.

The backoff policy mirrors :class:`phronesis._internal.retry.ExponentialBackoff`.
Per the protocol, a node returning ``RunOutcome.fail`` is *not* a raised
exception - it is a structured failure. Retry rewraps that failure into
the configured exception types so the same backoff machinery applies.
"""

from __future__ import annotations

import asyncio
from dataclasses import dataclass
from typing import Any

from phronesis._internal.retry.backoff import ExponentialBackoff
from phronesis.runtime.context import ExecutionContext
from phronesis.runtime.errors import ExecutionFailedError
from phronesis.runtime.obs import RUNTIME_ITERATION, runtime_span
from phronesis.runtime.outcome import RunOutcome
from phronesis.runtime.protocol import Executable


@dataclass(frozen=True, slots=True)
class Retry:
    """Retry ``node`` up to ``max_attempts`` times with exponential backoff.

    Attributes:
        node: Executable to invoke.
        max_attempts: Hard cap on attempts. Must be ``>= 1``.
        backoff_initial_s: Seed delay for exponential backoff.
        backoff_multiplier: Reserved for future strategies; kept for API
            parity with ``ExponentialBackoff``.
        backoff_max_s: Upper bound on a single delay.
        on: Exception types that trigger a retry. Defaults to
            ``(Exception,)`` so any raised error is retried.
    """

    node: Executable
    max_attempts: int = 3
    backoff_initial_s: float = 0.5
    backoff_multiplier: float = 2.0
    backoff_max_s: float = 30.0
    on: tuple[type[Exception], ...] = (Exception,)

    async def __call__(self, ctx: ExecutionContext, input: Any) -> RunOutcome:
        backoff = ExponentialBackoff(
            initial=self.backoff_initial_s,
            max_delay=self.backoff_max_s,
            jitter=False,
        )

        async with runtime_span("retry", run_id=ctx.run_id.canonical):
            last_outcome: RunOutcome | None = None

            for attempt in range(1, self.max_attempts + 1):
                try:
                    outcome = await self.node(
                        ctx.child(metadata={RUNTIME_ITERATION: attempt}),
                        input,
                    )
                except self.on as exc:
                    outcome = RunOutcome.fail(error=exc)

                last_outcome = outcome

                if outcome.success:
                    return outcome

                err = outcome.error
                retryable = err is not None and isinstance(err, self.on)

                if not retryable or attempt == self.max_attempts:
                    break

                await asyncio.sleep(backoff.get_delay(attempt))

            assert last_outcome is not None

            return RunOutcome.fail(
                error=last_outcome.error or ExecutionFailedError("retry exhausted without success"),
                output=last_outcome.output,
                metadata={RUNTIME_ITERATION: self.max_attempts},
            )
