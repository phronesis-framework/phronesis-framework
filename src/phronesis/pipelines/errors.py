"""Error hierarchy for the :mod:`phronesis.pipelines` package.

All pipeline-level failures inherit from :class:`PipelineError`. The
hierarchy is intentionally tiny in v1: pipelines compose ``Executable``
instances that already raise their own typed errors, so the only failure
modes the pipeline itself owns are structural (empty definition).
"""

from __future__ import annotations


class PipelineError(RuntimeError):
    """Base class for failures originating in :mod:`phronesis.pipelines`."""

    code: str = "pipeline_error"


class PipelineEmptyError(PipelineError):
    """A :class:`Pipeline` was invoked without any steps."""

    code = "pipeline_empty"
