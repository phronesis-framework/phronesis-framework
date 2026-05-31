"""Public API of the :mod:`phronesis.agents` package.

This package contains everything needed to declare, register, validate
and execute agents:

* :class:`Agent` and the :func:`agent` decorator declare new agents.
* :class:`AgentSpec` is the pure-data description of an agent.
* :class:`Session` runs multi-turn conversations against a stateless
  agent.
* :class:`RunRequest` and :class:`Result` are the call-cycle types.
* :class:`AgentEvent` is the union of streaming event types.
* :func:`agent_scope` and :func:`current_registry` give per-context
  isolation of declared agents.
* The ``Agent*Error`` hierarchy plus :class:`EmptySystemPromptWarning`
  cover every diagnostic the package raises.

Only names listed in ``__all__`` are part of the public contract.
Anything else is internal and may change without notice.
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
