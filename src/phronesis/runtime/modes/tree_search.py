"""Tree search: expand-evaluate beam search bounded by depth and width.

At each depth the current beam is expanded into candidate children, each
candidate is scored by ``evaluator``, and the top ``beam_width`` are kept
for the next round. The best leaf at the end is returned.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from phronesis.runtime.context import ExecutionContext
from phronesis.runtime.errors import ExecutionFailedError
from phronesis.runtime.obs import RUNTIME_ITERATION, runtime_span
from phronesis.runtime.outcome import RunOutcome
from phronesis.runtime.protocol import Executable


def _collect_expanded(output: Any, candidates: list[Any]) -> None:
    if isinstance(output, (list, tuple)):
        candidates.extend(output)
    else:
        candidates.append(output)


def _fail(
    error: Exception,
    children_log: list[RunOutcome],
) -> RunOutcome:
    return RunOutcome.fail(
        error=error,
        children=tuple(children_log),
    ).merge_children()


@dataclass(frozen=True, slots=True)
class TreeSearch:
    """Beam search via ``expander`` and ``evaluator`` executables.

    Attributes:
        expander: Executable producing a list of children from a node.
        evaluator: Executable returning a numeric score for a node.
        max_depth: Maximum depth of the search.
        beam_width: Number of best candidates kept per depth.
    """

    expander: Executable
    evaluator: Executable
    max_depth: int = 3
    beam_width: int = 3

    async def _expand_beam(
        self,
        ctx: ExecutionContext,
        beam: list[Any],
        depth: int,
        children_log: list[RunOutcome],
    ) -> tuple[list[Any] | None, RunOutcome | None]:
        candidates: list[Any] = []

        for node in beam:
            outcome = await self.expander(
                ctx.child(metadata={RUNTIME_ITERATION: depth}),
                node,
            )
            children_log.append(outcome)

            if not outcome.success:
                return None, _fail(
                    outcome.error or ExecutionFailedError("expander failed"),
                    children_log,
                )

            _collect_expanded(outcome.output, candidates)

        return candidates, None

    async def _score_candidates(
        self,
        ctx: ExecutionContext,
        candidates: list[Any],
        children_log: list[RunOutcome],
    ) -> tuple[list[tuple[float, Any]] | None, RunOutcome | None]:
        scored: list[tuple[float, Any]] = []

        for cand in candidates:
            outcome = await self.evaluator(ctx.child(), cand)
            children_log.append(outcome)

            if not outcome.success:
                return None, _fail(
                    outcome.error or ExecutionFailedError("evaluator failed"),
                    children_log,
                )

            try:
                score = float(outcome.output)
            except (TypeError, ValueError) as exc:
                return None, _fail(
                    ExecutionFailedError(f"evaluator did not return a number: {exc}"),
                    children_log,
                )

            scored.append((score, cand))

        return scored, None

    async def __call__(self, ctx: ExecutionContext, input: Any) -> RunOutcome:
        async with runtime_span("tree_search", run_id=ctx.run_id.canonical):
            beam: list[Any] = [input]
            children_log: list[RunOutcome] = []
            best: tuple[float, Any] | None = None

            for depth in range(1, self.max_depth + 1):
                candidates, failure = await self._expand_beam(ctx, beam, depth, children_log)

                if failure is not None:
                    return failure

                assert candidates is not None

                if not candidates:
                    break

                scored, failure = await self._score_candidates(ctx, candidates, children_log)

                if failure is not None:
                    return failure

                assert scored is not None

                scored.sort(key=lambda pair: pair[0], reverse=True)
                top = scored[: self.beam_width]

                if best is None or (top and top[0][0] > best[0]):
                    best = top[0]

                beam = [cand for _, cand in top]

            if best is None:
                return _fail(
                    ExecutionFailedError("tree search produced no candidates"),
                    children_log,
                )

            return RunOutcome.ok(
                output=best[1],
                children=tuple(children_log),
                metadata={"runtime.tree_search.score": best[0]},
            ).merge_children()
