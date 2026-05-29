"""Public API of the :mod:`phronesis.agents` package.

Re-exports will land here as each phase completes. See
``docs/AGENTS-DECISIONS.md`` for the full design.
"""

from __future__ import annotations

from phronesis.agents.errors import (
    AgentConfigurationError,
    AgentError,
    AgentExecutionError,
    AgentMaxIterationsError,
    AgentOutputValidationError,
    DuplicateAgentError,
)
from phronesis.agents.id import AgentId, agent_id_generator

__all__ = [
    "AgentConfigurationError",
    "AgentError",
    "AgentExecutionError",
    "AgentId",
    "AgentMaxIterationsError",
    "AgentOutputValidationError",
    "DuplicateAgentError",
    "agent_id_generator",
]
