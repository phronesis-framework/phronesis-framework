"""Stable identifier for declared :class:`Pipeline` instances.

A :class:`PipelineId` mirrors the pattern used by :class:`RunId` and
:class:`AgentId`: a definition-time hash of a canonical string, with a
short display form built from a fixed ``prefix``.

The canonical string follows the convention
``phronesis.pipelines.pipeline.<name>`` so two pipelines declared with
the same name resolve to the same id across processes.
"""

from __future__ import annotations

import re

from phronesis._internal.ids.generator import IdGenerator
from phronesis._internal.ids.id import Id

_INVALID_CHARS = re.compile(r"[^a-z0-9_]")
_LEADING_DIGITS = re.compile(r"^[0-9]+")


class PipelineId(Id):
    """Stable identifier for a :class:`Pipeline` declaration.

    Distinct from :class:`phronesis.runtime.context.RunId` because the
    pipeline identity survives across runs while the run id is fresh on
    each invocation.
    """

    prefix = "PID"


pipeline_id_generator: IdGenerator[PipelineId] = IdGenerator(PipelineId)
"""Process-wide :class:`IdGenerator` bound to :class:`PipelineId`."""


def _sanitize_segment(name: str) -> str:
    """Coerce ``name`` to a valid canonical-id segment.

    The :class:`CanonicalIdValidator` only accepts ``[a-z_][a-z0-9_]*``
    segments. Pipeline names are user-facing strings that may include
    spaces, hyphens or uppercase letters; this helper normalises them so
    the canonical id stays valid without forcing callers to mirror the
    constraint manually.
    """
    lowered = name.strip().lower()
    safe = _INVALID_CHARS.sub("_", lowered)
    safe = _LEADING_DIGITS.sub("_", safe)

    return safe or "_"


def _new_pipeline_id(name: str) -> PipelineId:
    """Derive a :class:`PipelineId` from a pipeline name.

    The canonical form is ``phronesis.pipelines.pipeline.<segment>``
    where ``<segment>`` is the normalised form of ``name`` and is stable
    across processes for the same input.
    """
    canonical = f"phronesis.pipelines.pipeline.{_sanitize_segment(name)}"

    return pipeline_id_generator.from_canonical(canonical)
