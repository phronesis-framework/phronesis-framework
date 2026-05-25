"""Stable internal identifier for a single agent run."""

from __future__ import annotations

from phronesis._internal.ids.generator import IdGenerator
from phronesis._internal.ids.id import Id


class RunId(Id):
    """Identifier for one execution of an agent."""

    prefix = "RID"


run_id_generator: IdGenerator[RunId] = IdGenerator(RunId)
"""Singleton :class:`IdGenerator` for :class:`RunId`."""
