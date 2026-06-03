"""Pipeline: named, identifiable orchestration over a linear graph.

A :class:`Pipeline` wraps a tuple of :class:`Executable` steps and runs
them sequentially, threading each step's output as the next step's
input. Unlike :class:`phronesis.runtime.Sequence`, a :class:`Pipeline`
carries identity (``name`` + :class:`PipelineId`) and emits a dedicated
``phronesis.runtime.pipeline`` span with :data:`PIPELINE_ID` /
:data:`PIPELINE_NAME` attributes.

Non-lineal topologies (fan-out, races, branches, ...) are expressed by
nesting any :mod:`phronesis.runtime` mode as one of the steps.
"""

from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass
from typing import Any

from phronesis.obs.attributes import PIPELINE_ID, PIPELINE_NAME
from phronesis.pipelines.errors import PipelineEmptyError
from phronesis.pipelines.ids import PipelineId, _new_pipeline_id
from phronesis.runtime.context import ExecutionContext
from phronesis.runtime.errors import CancelledError, ExecutionFailedError
from phronesis.runtime.node import as_node
from phronesis.runtime.obs import RUNTIME_CHILDREN_COUNT, runtime_span
from phronesis.runtime.outcome import RunOutcome
from phronesis.runtime.protocol import Executable


@dataclass(frozen=True, slots=True)
class Pipeline:
    """Named, identifiable orchestration over a linear graph of Executables.

    Attributes:
        name: Logical name used in spans and metrics as ``pipeline.name``.
        steps: Tuple of :class:`Executable` nodes; output of step ``N``
            becomes the input of step ``N+1``.
        pipeline_id: Stable :class:`PipelineId` for OTEL correlation.
    """

    name: str
    steps: tuple[Executable, ...]
    pipeline_id: PipelineId

    async def __call__(self, ctx: ExecutionContext, input: Any) -> RunOutcome:
        extra = {
            PIPELINE_ID: self.pipeline_id.canonical,
            PIPELINE_NAME: self.name,
        }

        async with runtime_span(
            "pipeline",
            run_id=ctx.run_id.canonical,
            parent_id=ctx.parent_id.canonical if ctx.parent_id is not None else None,
            extra=extra,
        ):
            if not self.steps:
                return RunOutcome.fail(
                    error=PipelineEmptyError(f"pipeline {self.name!r} has no steps"),
                )

            children: list[RunOutcome] = []
            current: Any = input

            for step in self.steps:
                if ctx.is_cancelled():
                    return RunOutcome.fail(
                        error=CancelledError(f"pipeline {self.name!r} cancelled"),
                        children=tuple(children),
                        metadata={RUNTIME_CHILDREN_COUNT: len(children)},
                    ).merge_children()

                child_ctx = ctx.child()
                outcome = await step(child_ctx, current)
                children.append(outcome)

                if not outcome.success:
                    error = outcome.error or ExecutionFailedError(
                        f"step failed in pipeline {self.name!r}"
                    )

                    return RunOutcome.fail(
                        error=error,
                        output=outcome.output,
                        children=tuple(children),
                        metadata={RUNTIME_CHILDREN_COUNT: len(children)},
                    ).merge_children()

                current = outcome.output

            return RunOutcome.ok(
                output=current,
                children=tuple(children),
                metadata={RUNTIME_CHILDREN_COUNT: len(children)},
            ).merge_children()

    async def run(
        self,
        input: Any,
        *,
        deadline_s: float | None = None,
        metadata: Mapping[str, Any] | None = None,
    ) -> RunOutcome:
        """Convenience entry point that builds a fresh root context.

        Args:
            input: Initial value passed to the first step.
            deadline_s: Wall-clock cap for the whole pipeline, forwarded
                to :meth:`ExecutionContext.new`.
            metadata: Initial metadata mapping for the root context.
        """
        ctx = ExecutionContext.new(deadline_s=deadline_s, metadata=metadata)

        return await self(ctx, input)


def pipeline(
    *steps: Any,
    name: str,
    pipeline_id: PipelineId | None = None,
) -> Pipeline:
    """Build a :class:`Pipeline` from heterogeneous steps.

    Each positional argument is adapted via :func:`as_node`, so agents,
    async callables and existing :class:`Executable` instances all work
    without explicit wrapping.

    Args:
        *steps: Steps to run in order.
        name: Logical pipeline name (required, keyword-only).
        pipeline_id: Pre-computed :class:`PipelineId`. When omitted, the
            id is derived from ``name`` via :func:`_new_pipeline_id`.
    """
    adapted: tuple[Executable, ...] = tuple(as_node(step) for step in steps)
    pid = pipeline_id if pipeline_id is not None else _new_pipeline_id(name)

    return Pipeline(name=name, steps=adapted, pipeline_id=pid)
