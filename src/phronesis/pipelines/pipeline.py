"""Pipeline: named, identifiable orchestration over a linear graph.

A :class:`Pipeline` wraps a tuple of :class:`Executable` steps and runs
them sequentially, threading each step's output as the next step's
input. Unlike :class:`phronesis.runtime.Sequence`, a :class:`Pipeline`
carries identity (``name`` + :class:`PipelineId`) and emits a dedicated
``phronesis.runtime.pipeline`` span with :data:`PIPELINE_ID` /
:data:`PIPELINE_NAME` attributes.

Two declaration styles share a single :func:`pipeline` callable:

* **Imperative factory** - ``pipeline(*steps, name=...)`` returns a
  :class:`Pipeline` directly. Convenient when steps are already in
  scope.
* **Decorator** - ``@pipeline(steps=(...), name=None)`` wraps a
  function used purely as a metadata carrier. ``__name__`` provides the
  default ``name``, ``__doc__`` becomes the ``description`` and the
  ``module.qualname`` derives the :class:`PipelineId` (same convention
  as :func:`phronesis.agents.agent`).

Non-lineal topologies (fan-out, races, branches, ...) are expressed by
nesting any :mod:`phronesis.runtime` mode as one of the steps.
"""

from __future__ import annotations

import inspect
from collections.abc import Callable, Iterable, Mapping
from dataclasses import dataclass, field
from typing import Any, overload

from phronesis.obs.attributes import PIPELINE_ID, PIPELINE_NAME
from phronesis.pipelines.errors import PipelineEmptyError
from phronesis.pipelines.ids import PipelineId, _new_pipeline_id, pipeline_id_generator
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
        description: Optional free-form description seeded from the
            decorated function's docstring when using the ``@pipeline``
            decorator. Empty by default.
    """

    name: str
    steps: tuple[Executable, ...]
    pipeline_id: PipelineId
    description: str = field(default="")

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


def _build_factory_pipeline(
    positional_steps: tuple[Any, ...],
    *,
    name: str,
    pipeline_id: PipelineId | None,
) -> Pipeline:
    """Materialise a :class:`Pipeline` from positional steps."""
    adapted: tuple[Executable, ...] = tuple(as_node(step) for step in positional_steps)
    pid = pipeline_id if pipeline_id is not None else _new_pipeline_id(name)

    return Pipeline(name=name, steps=adapted, pipeline_id=pid)


def _build_decorator_pipeline(
    fn: Callable[..., Any],
    *,
    declared_steps: tuple[Any, ...],
    name: str | None,
    pipeline_id: PipelineId | None,
) -> Pipeline:
    """Materialise a :class:`Pipeline` from a function used as metadata.

    The function body is intentionally ignored - only ``__name__``,
    ``__doc__`` and ``module.qualname`` are consulted, mirroring the
    convention used by :func:`phronesis.agents.agent`.
    """
    resolved_name = name if name is not None else fn.__name__
    resolved_description = inspect.getdoc(fn) or ""

    if pipeline_id is not None:
        resolved_id = pipeline_id
    else:
        resolved_id = pipeline_id_generator.from_function(fn)

    adapted: tuple[Executable, ...] = tuple(as_node(step) for step in declared_steps)

    return Pipeline(
        name=resolved_name,
        steps=adapted,
        pipeline_id=resolved_id,
        description=resolved_description,
    )


@overload
def pipeline(
    *steps: Any,
    name: str,
    pipeline_id: PipelineId | None = None,
) -> Pipeline: ...


@overload
def pipeline(
    *,
    steps: Iterable[Any],
    name: str | None = None,
    pipeline_id: PipelineId | None = None,
) -> Callable[[Callable[..., Any]], Pipeline]: ...


def pipeline(
    *positional_steps: Any,
    name: str | None = None,
    pipeline_id: PipelineId | None = None,
    steps: Iterable[Any] | None = None,
) -> Pipeline | Callable[[Callable[..., Any]], Pipeline]:
    """Declare a :class:`Pipeline` imperatively or as a decorator.

    **Factory mode** - positional ``*steps`` plus a required ``name``::

        p = pipeline(fetch, parse, summarize, name="ingestion")

    **Decorator mode** - keyword-only ``steps=`` applied to a function
    that acts purely as metadata carrier::

        @pipeline(steps=(fetch, parse, summarize))
        def ingestion() -> None:
            \"\"\"Pull a URL and produce a summary.\"\"\"

    In decorator mode ``name`` defaults to ``fn.__name__``,
    ``description`` is seeded from ``fn.__doc__`` and the
    :class:`PipelineId` is derived from the function's
    ``module.qualname`` so the identity is unique per declaration site.

    Args:
        *positional_steps: Steps to run in order (factory mode). Mutually
            exclusive with ``steps=``.
        name: Logical pipeline name. Required in factory mode; optional
            in decorator mode (defaults to ``fn.__name__``).
        pipeline_id: Pre-computed :class:`PipelineId` that overrides the
            default identity derivation.
        steps: Tuple of steps declared via the decorator form. Mutually
            exclusive with positional arguments.
    """
    if steps is not None:
        if positional_steps:
            raise TypeError(
                "pipeline() cannot mix positional steps and the 'steps=' keyword argument"
            )

        declared = tuple(steps)

        def _decorator(fn: Callable[..., Any]) -> Pipeline:
            return _build_decorator_pipeline(
                fn,
                declared_steps=declared,
                name=name,
                pipeline_id=pipeline_id,
            )

        return _decorator

    if name is None:
        raise TypeError("pipeline() requires 'name' in factory mode")

    return _build_factory_pipeline(positional_steps, name=name, pipeline_id=pipeline_id)
