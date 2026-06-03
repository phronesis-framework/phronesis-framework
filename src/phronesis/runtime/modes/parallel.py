"""Concurrent fan-out with configurable error policy.

Every node receives the same input and runs concurrently. The
:class:`GatherPolicy` controls failure semantics: :class:`FailFastPolicy`
(default) cancels remaining nodes on first error; :class:`BestEffortPolicy`
waits for everyone and surfaces partial failures.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

from phronesis._internal.concurrency import (
    FailFastPolicy,
    GatherPolicy,
    PartialFailureError,
    gather_all,
)
from phronesis.runtime.context import ExecutionContext
from phronesis.runtime.obs import runtime_span
from phronesis.runtime.outcome import RunOutcome
from phronesis.runtime.protocol import Executable


def _coerce(exc: BaseException | None) -> Exception:
    if isinstance(exc, Exception):
        return exc

    return Exception(str(exc) if exc else "unknown error")


@dataclass(frozen=True, slots=True)
class Parallel:
    """Run nodes concurrently with the same input; return tuple of outputs.

    Attributes:
        nodes: Tuple of executables to invoke in parallel.
        policy: Error-handling strategy delegated to
            :func:`gather_all`. Defaults to :class:`FailFastPolicy`.
    """

    nodes: tuple[Executable, ...]
    policy: GatherPolicy = field(default_factory=FailFastPolicy)

    async def __call__(self, ctx: ExecutionContext, input: Any) -> RunOutcome:
        async with runtime_span("parallel", run_id=ctx.run_id.canonical):
            child_ctxs = [ctx.child() for _ in self.nodes]
            awaitables = [
                node(child_ctx, input)
                for node, child_ctx in zip(self.nodes, child_ctxs, strict=True)
            ]

            try:
                results = await gather_all(*awaitables, policy=self.policy)
            except PartialFailureError as exc:
                outcomes: tuple[RunOutcome, ...] = tuple(
                    r if isinstance(r, RunOutcome) else RunOutcome.fail(error=_coerce(e))
                    for r, e in zip(exc.results, exc.exceptions, strict=True)
                )

                return RunOutcome.fail(
                    error=exc,
                    output=tuple(o.output for o in outcomes),
                    children=outcomes,
                ).merge_children()
            except Exception as exc:
                return RunOutcome.fail(error=exc).merge_children()

            outcomes = tuple(results)
            outputs = tuple(o.output for o in outcomes)

            failed = next((o for o in outcomes if not o.success), None)

            if failed is not None:
                return RunOutcome.fail(
                    error=failed.error or Exception("parallel node failed"),
                    output=outputs,
                    children=outcomes,
                ).merge_children()

            return RunOutcome.ok(output=outputs, children=outcomes).merge_children()
