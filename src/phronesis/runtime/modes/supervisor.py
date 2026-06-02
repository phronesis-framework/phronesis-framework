"""Supervisor: a supervisor agent routes work to named workers.

The supervisor's output decides the next worker via ``route_extractor``.
The default extractor accepts either a ``dict`` with a ``"route"`` key or
any object exposing a ``route`` attribute. When the supervisor produces
no route, the loop terminates with the supervisor's last output.
"""

from __future__ import annotations

from collections.abc import Callable, Mapping
from dataclasses import dataclass, field
from typing import Any

from phronesis.runtime.context import ExecutionContext
from phronesis.runtime.errors import CancelledError, LoopExhaustedError
from phronesis.runtime.obs import RUNTIME_ITERATION, RUNTIME_ROUTE, runtime_span
from phronesis.runtime.outcome import RunOutcome
from phronesis.runtime.protocol import Executable


def default_route_extractor(output: Any) -> str | None:
    """Pull a route key out of a ``dict`` or attribute on ``output``."""
    if isinstance(output, Mapping):
        route = output.get("route")

        return str(route) if route is not None else None

    route = getattr(output, "route", None)

    return str(route) if route is not None else None


@dataclass(frozen=True, slots=True)
class Supervisor:
    """Supervisor agent decides which worker to invoke each iteration.

    Attributes:
        supervisor: Executable acting as the dispatcher.
        workers: Mapping of route key to worker executable.
        max_iterations: Hard cap on supervisor/worker round-trips.
        route_extractor: Callable extracting a route key from the
            supervisor output. ``None`` signals termination.
    """

    supervisor: Executable
    workers: Mapping[str, Executable]
    max_iterations: int = 10
    route_extractor: Callable[[Any], str | None] = field(default=default_route_extractor)

    async def __call__(self, ctx: ExecutionContext, input: Any) -> RunOutcome:
        async with runtime_span("supervisor", run_id=ctx.run_id.canonical):
            children: list[RunOutcome] = []
            current: Any = input

            for iteration in range(1, self.max_iterations + 1):
                if ctx.is_cancelled():
                    return RunOutcome.fail(
                        error=CancelledError("supervisor cancelled"),
                        children=tuple(children),
                    ).merge_children()

                sup_outcome = await self.supervisor(
                    ctx.child(metadata={RUNTIME_ITERATION: iteration}),
                    current,
                )
                children.append(sup_outcome)

                if not sup_outcome.success:
                    return RunOutcome.fail(
                        error=sup_outcome.error or Exception("supervisor failed"),
                        children=tuple(children),
                    ).merge_children()

                route = self.route_extractor(sup_outcome.output)

                if route is None:
                    return RunOutcome.ok(
                        output=sup_outcome.output,
                        children=tuple(children),
                        metadata={RUNTIME_ITERATION: iteration},
                    ).merge_children()

                worker = self.workers.get(route)

                if worker is None:
                    return RunOutcome.fail(
                        error=KeyError(f"no worker for route {route!r}"),
                        children=tuple(children),
                        metadata={RUNTIME_ROUTE: route},
                    ).merge_children()

                worker_outcome = await worker(
                    ctx.child(metadata={RUNTIME_ROUTE: route, RUNTIME_ITERATION: iteration}),
                    sup_outcome.output,
                )
                children.append(worker_outcome)

                if not worker_outcome.success:
                    return RunOutcome.fail(
                        error=worker_outcome.error or Exception(f"worker {route!r} failed"),
                        children=tuple(children),
                    ).merge_children()

                current = worker_outcome.output

            return RunOutcome.fail(
                error=LoopExhaustedError(
                    f"supervisor reached max_iterations={self.max_iterations}",
                ),
                output=current,
                children=tuple(children),
            ).merge_children()
