"""Identifier types for agents.

See ``docs/AGENTS-DECISIONS.md`` (D-04): agents carry a stable
:class:`AgentId` derived from the declaring function. The framework
uses this id for registry lookups, span attributes and serialization.
"""

from __future__ import annotations

from phronesis._internal.ids.generator import IdGenerator
from phronesis._internal.ids.id import Id


class AgentId(Id):
    """Stable internal identifier for a declared agent."""

    prefix = "AID"


agent_id_generator: IdGenerator[AgentId] = IdGenerator(AgentId)
"""Singleton :class:`IdGenerator` for :class:`AgentId`."""
