"""Identifier types for agents.

Every declared agent carries a stable :class:`AgentId` whose canonical
form is derived from the declaring function's dotted path. The id is
used as the registry key, as the value of the ``agent.id`` span
attribute and as the agent identifier in serialized payloads.

The module exposes a singleton :data:`agent_id_generator` for parsing
and validating canonical strings.
"""

from __future__ import annotations

from phronesis._internal.ids.generator import IdGenerator
from phronesis._internal.ids.id import Id


class AgentId(Id):
    """Stable internal identifier for a declared agent.

    Subclass of :class:`phronesis._internal.ids.id.Id` that fixes the
    short prefix to ``"AID"``. Instances are created from a canonical
    string (e.g. ``"phronesis.agents.example.greeter"``) and validated
    by the base class.
    """

    prefix = "AID"


agent_id_generator: IdGenerator[AgentId] = IdGenerator(AgentId)
"""Process-wide :class:`IdGenerator` bound to :class:`AgentId`.

Use ``agent_id_generator.from_canonical(text)`` to validate and parse a
canonical agent id without instantiating a generator.
"""
