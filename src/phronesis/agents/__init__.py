"""Public API of the :mod:`phronesis.agents` package.

Re-exports the supported surface of the agents module. Anything not
listed here is internal and subject to change without notice. See
``docs/AGENTS-DECISIONS.md`` for the full design.
"""

from __future__ import annotations

from phronesis.agents.agent import Agent
from phronesis.agents.decorator import agent
from phronesis.agents.errors import (
    AgentConfigurationError,
    AgentError,
    AgentExecutionError,
    AgentMaxIterationsError,
    AgentOutputValidationError,
    DuplicateAgentError,
)
from phronesis.agents.events import (
    AgentEvent,
    RunCompleted,
    RunFailed,
    RunStarted,
    TextDelta,
    ToolCallCompleted,
    ToolCallStarted,
)
from phronesis.agents.id import AgentId, agent_id_generator
from phronesis.agents.registry import (
    AgentNotFoundError,
    agent_scope,
    current_registry,
)
from phronesis.agents.run import Result, RunId, RunRequest, TokenUsage
from phronesis.agents.session import Session
from phronesis.agents.spec import AgentSpec
from phronesis.agents.validation import EmptySystemPromptWarning

__all__ = [
    "Agent",
    "AgentConfigurationError",
    "AgentError",
    "AgentEvent",
    "AgentExecutionError",
    "AgentId",
    "AgentMaxIterationsError",
    "AgentNotFoundError",
    "AgentOutputValidationError",
    "AgentSpec",
    "DuplicateAgentError",
    "EmptySystemPromptWarning",
    "Result",
    "RunCompleted",
    "RunFailed",
    "RunId",
    "RunRequest",
    "RunStarted",
    "Session",
    "TextDelta",
    "TokenUsage",
    "ToolCallCompleted",
    "ToolCallStarted",
    "agent",
    "agent_id_generator",
    "agent_scope",
    "current_registry",
]
