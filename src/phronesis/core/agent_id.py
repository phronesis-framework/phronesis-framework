"""Stable internal identifier for a declared agent."""

from __future__ import annotations

from phronesis._internal.ids.generator import IdGenerator
from phronesis._internal.ids.id import Id


class AgentId(Id):
    """Identifier for an agent definition."""

    prefix = "AID"


agent_id_generator: IdGenerator[AgentId] = IdGenerator(AgentId)
"""Singleton :class:`IdGenerator` for :class:`AgentId`."""
