"""Race: first successful node wins; the rest are cancelled."""

from __future__ import annotations

import asyncio
import contextlib
from dataclasses import dataclass
from typing import Any

from phronesis.runtime.context import ExecutionContext
from phronesis.runtime.errors import ExecutionFailedError
from phronesis.runtime.obs import runtime_span
from phronesis.runtime.outcome import RunOutcome
from phronesis.runtime.protocol import Executable


@dataclass(frozen=True, slots=True)
class Race:
    """First node to complete successfully wins.

    Losing tasks are cancelled cooperatively; modes that depend on agent
    or provider cancellation must respect ``asyncio.CancelledError`` for
    the cancellation to take effect.

    Attributes:
        nodes: Tuple of executables to race.
    """

    nodes: tuple[Executable, ...]

    async def __call__(self, ctx: ExecutionContext, input: Any) -> RunOutcome:
        async with runtime_span("race", run_id=ctx.run_id.canonical):
            if not self.nodes:
                return RunOutcome.fail(error=ExecutionFailedError("race with no nodes"))

            tasks: list[asyncio.Task[RunOutcome]] = [
                asyncio.create_task(node(ctx.child(), input)) for node in self.nodes
            ]

            try:
                last_error: Exception | None = None
                pending = set(tasks)

                while pending:
                    done, pending = await asyncio.wait(pending, return_when=asyncio.FIRST_COMPLETED)

                    for task in done:
                        try:
                            outcome = task.result()
                        except Exception as exc:
                            last_error = exc

                            continue

                        if outcome.success:
                            return RunOutcome.ok(
                                output=outcome.output,
                                tokens=outcome.tokens,
                                cost_usd=outcome.cost_usd,
                            )

                        last_error = outcome.error or last_error

                return RunOutcome.fail(
                    error=last_error or ExecutionFailedError("all racers failed")
                )
            finally:
                for task in tasks:
                    if not task.done():
                        task.cancel()

                for task in tasks:
                    if not task.done():
                        with contextlib.suppress(BaseException):
                            await task
