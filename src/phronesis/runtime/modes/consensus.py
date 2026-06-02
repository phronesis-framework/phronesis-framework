"""Consensus: voters answer in parallel; an aggregator combines results."""

from __future__ import annotations

from collections import Counter
from collections.abc import Callable
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
from phronesis.runtime.errors import ConsensusError
from phronesis.runtime.obs import runtime_span
from phronesis.runtime.outcome import RunOutcome
from phronesis.runtime.protocol import Executable


def majority_aggregator(outputs: SeqAlias[Any]) -> Any:
    """Return the most common output. Ties broken by insertion order."""
    try:
        counts = Counter(outputs)
    except TypeError:
        return outputs[0] if outputs else None

    most = counts.most_common(1)

    return most[0][0] if most else None


@dataclass(frozen=True, slots=True)
class Consensus:
    """Voters run in parallel; ``aggregator`` produces the consensus value.

    Attributes:
        voters: Tuple of voter executables.
        aggregator: Callable folding the per-voter outputs into a final
            value. Defaults to :func:`majority_aggregator`.
        min_agreement: Minimum fraction of voters that must agree with
            the aggregated value (``0.5`` = half). When fewer voters
            agree the mode fails with :class:`ConsensusError`.
    """

    voters: tuple[Executable, ...]
    aggregator: Callable[[SeqAlias[Any]], Any] = field(default=majority_aggregator)
    min_agreement: float = 0.5

    async def __call__(self, ctx: ExecutionContext, input: Any) -> RunOutcome:
        async with runtime_span("consensus", run_id=ctx.run_id.canonical):
            awaitables = [voter(ctx.child(), input) for voter in self.voters]

            try:
                results: list[RunOutcome] = list(
                    await gather_all(*awaitables, policy=FailFastPolicy())
                )
            except PartialFailureError as exc:
                return RunOutcome.fail(error=exc).merge_children()
            except Exception as exc:
                return RunOutcome.fail(error=exc).merge_children()

            failed = next((r for r in results if not r.success), None)

            if failed is not None:
                return RunOutcome.fail(
                    error=failed.error or Exception("voter failed"),
                    children=tuple(results),
                ).merge_children()

            outputs = [r.output for r in results]
            aggregated = self.aggregator(outputs)

            try:
                agree = sum(1 for o in outputs if o == aggregated)
            except Exception:
                agree = 0

            fraction = agree / len(outputs) if outputs else 0.0

            if fraction < self.min_agreement:
                return RunOutcome.fail(
                    error=ConsensusError(
                        f"consensus not reached: {fraction:.2f} < {self.min_agreement:.2f}",
                        details={"agreement": fraction, "required": self.min_agreement},
                    ),
                    children=tuple(results),
                ).merge_children()

            return RunOutcome.ok(
                output=aggregated,
                children=tuple(results),
                metadata={"runtime.consensus.agreement": fraction},
            ).merge_children()

    def _unused(self) -> GatherPolicy:  # pragma: no cover - typing aid
        return FailFastPolicy()
