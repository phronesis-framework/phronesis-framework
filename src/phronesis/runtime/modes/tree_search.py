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

    async def __call__(self, ctx: ExecutionContext, input: Any) -> RunOutcome:
        async with runtime_span("tree_search", run_id=ctx.run_id.canonical):
            beam: list[Any] = [input]
            children_log: list[RunOutcome] = []
            best: tuple[float, Any] | None = None

            for depth in range(1, self.max_depth + 1):
                candidates: list[Any] = []

                for node in beam:
                    expand_outcome = await self.expander(
                        ctx.child(metadata={RUNTIME_ITERATION: depth}),
                        node,
                    )
                    children_log.append(expand_outcome)

                    if not expand_outcome.success:
                        return RunOutcome.fail(
                            error=expand_outcome.error or ExecutionFailedError("expander failed"),
                            children=tuple(children_log),
                        ).merge_children()

                    expanded = expand_outcome.output

                    if isinstance(expanded, (list, tuple)):
                        candidates.extend(expanded)
                    else:
                        candidates.append(expanded)

                if not candidates:
                    break

                scored: list[tuple[float, Any]] = []

                for cand in candidates:
                    eval_outcome = await self.evaluator(ctx.child(), cand)
                    children_log.append(eval_outcome)

                    if not eval_outcome.success:
                        return RunOutcome.fail(
                            error=eval_outcome.error or ExecutionFailedError("evaluator failed"),
                            children=tuple(children_log),
                        ).merge_children()

                    try:
                        score = float(eval_outcome.output)
                    except (TypeError, ValueError) as exc:
                        return RunOutcome.fail(
                            error=ExecutionFailedError(f"evaluator did not return a number: {exc}"),
                            children=tuple(children_log),
                        ).merge_children()

                    scored.append((score, cand))

                scored.sort(key=lambda pair: pair[0], reverse=True)
                top = scored[: self.beam_width]

                if best is None or (top and top[0][0] > best[0]):
                    best = top[0]

                beam = [cand for _, cand in top]

            if best is None:
                return RunOutcome.fail(
                    error=ExecutionFailedError("tree search produced no candidates"),
                    children=tuple(children_log),
                ).merge_children()

            return RunOutcome.ok(
                output=best[1],
                children=tuple(children_log),
                metadata={"runtime.tree_search.score": best[0]},
            ).merge_children()
