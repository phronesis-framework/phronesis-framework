"""Map-reduce: split input, map in parallel, reduce the results."""

from __future__ import annotations

import inspect
from collections.abc import Awaitable, Callable
from collections.abc import Sequence as SeqAlias
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
class MapReduce:
    """Split, map and reduce.

    Attributes:
        splitter: Pure function splitting the input into N items.
        mapper: Executable applied to each split item.
        reducer: Sync or async callable folding the mapped outputs.
        policy: Concurrency policy for the map phase.
    """

    splitter: Callable[[Any], SeqAlias[Any]]
    mapper: Executable
    reducer: Callable[[SeqAlias[Any]], Awaitable[Any] | Any]
    policy: GatherPolicy = field(default_factory=FailFastPolicy)

    async def __call__(self, ctx: ExecutionContext, input: Any) -> RunOutcome:
        async with runtime_span("map_reduce", run_id=ctx.run_id.canonical):
            items = list(self.splitter(input))
            child_ctxs = [ctx.child() for _ in items]
            awaitables = [
                self.mapper(child_ctx, item)
                for child_ctx, item in zip(child_ctxs, items, strict=True)
            ]

            try:
                mapped: list[RunOutcome] = list(await gather_all(*awaitables, policy=self.policy))
            except PartialFailureError as exc:
                outcomes: tuple[RunOutcome, ...] = tuple(
                    r if isinstance(r, RunOutcome) else RunOutcome.fail(error=_coerce(e))
                    for r, e in zip(exc.results, exc.exceptions, strict=True)
                )

                return RunOutcome.fail(error=exc, children=outcomes).merge_children()
            except Exception as exc:
                return RunOutcome.fail(error=exc).merge_children()

            failed = next((o for o in mapped if not o.success), None)

            if failed is not None:
                return RunOutcome.fail(
                    error=failed.error or Exception("mapper failed"),
                    children=tuple(mapped),
                ).merge_children()

            outputs = [o.output for o in mapped]
            reduced = self.reducer(outputs)

            if inspect.isawaitable(reduced):
                reduced = await reduced

            return RunOutcome.ok(output=reduced, children=tuple(mapped)).merge_children()
