"""Declarative composition of named :class:`Executable` graphs.

The :mod:`phronesis.pipelines` package adds identity, observability and
a top-level entry point on top of :mod:`phronesis.runtime`. A
:class:`Pipeline` is a frozen, named orchestration of executable steps
that runs through :meth:`Pipeline.run` (which builds a fresh
:class:`ExecutionContext`) or by calling the pipeline directly with an
existing context.

Linear pipelines compose with nested runtime modes (``Parallel``,
``Router``, ``Retry``, ...) so the v1 surface stays minimal while
covering DAG-shaped flows through composition.
"""

from __future__ import annotations

from phronesis.pipelines.errors import PipelineEmptyError, PipelineError
from phronesis.pipelines.ids import PipelineId, pipeline_id_generator
from phronesis.pipelines.pipeline import Pipeline, pipeline

__all__ = [
    "Pipeline",
    "PipelineEmptyError",
    "PipelineError",
    "PipelineId",
    "pipeline",
    "pipeline_id_generator",
]
