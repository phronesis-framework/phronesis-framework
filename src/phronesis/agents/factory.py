"""Programmatic construction of agents from a plain :class:`AgentSpec`.

The :func:`phronesis.agents.decorator.agent` decorator is the ergonomic
path when agents are known at import time. Callers that build agents
from data - a config file, a database row, a UI form - need the same
guarantees without a function to decorate: eager validation and
registration.

:func:`build_agent` is that entry point. The decorator delegates to it
so both paths share one definition of what "a declared agent" means.
"""

from __future__ import annotations

from phronesis.agents.agent import Agent
from phronesis.agents.registry import current_registry
from phronesis.agents.spec import AgentSpec
from phronesis.agents.validation import validate_spec


def build_agent(spec: AgentSpec, *, register: bool = True) -> Agent:
    """Validate ``spec`` and wrap it in a registered :class:`Agent`.

    Args:
        spec: The :class:`AgentSpec` to declare. Validated eagerly
            with :func:`validate_spec` before the wrapper is built.
        register: When ``True`` (the default) the agent is registered
            into the registry returned by :func:`current_registry`.
            Pass ``False`` for throwaway agents - per-session clones,
            tests - that must not claim a global id.

    Returns:
        The built :class:`Agent`.

    Raises:
        AgentConfigurationError: if ``spec`` fails validation.
        DuplicateAgentError: if ``register`` is ``True`` and another
            distinct agent already holds ``spec.id``.
    """
    validate_spec(spec)

    built = Agent(spec)

    if register:
        current_registry().register(built)

    return built
