"""Approval: gate the produced output behind a (possibly human) callback."""

from __future__ import annotations

import asyncio
import inspect
from collections.abc import Awaitable, Callable
from dataclasses import dataclass
from typing import Any

from phronesis.runtime.context import ExecutionContext
from phronesis.runtime.errors import ApprovalDeniedError, ApprovalTimeoutError
from phronesis.runtime.obs import runtime_span
from phronesis.runtime.outcome import RunOutcome
from phronesis.runtime.protocol import Executable


@dataclass(frozen=True, slots=True)
class Approval:
    """Run ``node`` and ask ``approve`` to accept the output.

    Attributes:
        node: Executable producing the candidate output.
        approve: Sync or async callable returning ``True`` to accept.
        timeout_s: Optional cap on how long ``approve`` may take. ``None``
            disables the timeout but is strongly discouraged when the
            callback waits for human input.
    """

    node: Executable
    approve: Callable[[Any], Awaitable[bool] | bool]
    timeout_s: float | None = None

    async def __call__(self, ctx: ExecutionContext, input: Any) -> RunOutcome:
        async with runtime_span("approval", run_id=ctx.run_id.canonical):
            outcome = await self.node(ctx.child(), input)

            if not outcome.success:
                return outcome

            try:
                verdict = await asyncio.wait_for(
                    _evaluate_approval(self.approve, outcome.output),
                    timeout=self.timeout_s,
                )
            except TimeoutError:
                return RunOutcome.fail(
                    error=ApprovalTimeoutError(
                        f"approval timed out after {self.timeout_s}s",
                        details={"timeout_s": self.timeout_s},
                    ),
                    output=outcome.output,
                )

            if not verdict:
                return RunOutcome.fail(
                    error=ApprovalDeniedError("approval denied"),
                    output=outcome.output,
                )

            return RunOutcome.ok(
                output=outcome.output,
                tokens=outcome.tokens,
                cost_usd=outcome.cost_usd,
            )


async def _evaluate_approval(
    approve: Callable[[Any], Awaitable[bool] | bool],
    candidate: Any,
) -> bool:
    """Call ``approve`` and await if it returns an awaitable."""
    verdict = approve(candidate)

    if inspect.isawaitable(verdict):
        verdict = await verdict

    return bool(verdict)
