"""Eager validation of :class:`AgentSpec` at decoration time.

See ``docs/AGENTS-DECISIONS.md`` (D-12). Configuration errors raise
:class:`AgentConfigurationError`; soft issues (empty system prompt)
emit a :class:`EmptySystemPromptWarning` so callers can act on them
without aborting agent construction.

Tool-provider compatibility is validated lazily on the first run; this
module focuses exclusively on the eager checks.
"""

from __future__ import annotations

import warnings

from phronesis.agents.errors import AgentConfigurationError
from phronesis.agents.spec import AgentSpec
from phronesis.providers.protocol import LLMProvider
from phronesis.tools.tool import Tool


class EmptySystemPromptWarning(UserWarning):
    """Warned when an agent is built with an empty system prompt."""


def validate_spec(spec: AgentSpec) -> None:
    """Run every eager check on ``spec``.

    Raises:
        AgentConfigurationError: if any structural rule fails.
    """
    _validate_model(spec)
    _validate_tools(spec)
    _validate_output_type(spec)
    _validate_max_iterations(spec)
    _validate_system_prompt(spec)


def _validate_model(spec: AgentSpec) -> None:
    if not isinstance(spec.model, LLMProvider):
        raise AgentConfigurationError(
            "Agent 'model' must implement the LLMProvider protocol.",
            details={"agent_id": spec.id.canonical, "model_type": type(spec.model).__name__},
        )


def _validate_tools(spec: AgentSpec) -> None:
    seen: set[str] = set()

    for tool in spec.tools:
        if not isinstance(tool, Tool):
            raise AgentConfigurationError(
                "Every entry in 'tools' must be a phronesis.tools.Tool instance.",
                details={
                    "agent_id": spec.id.canonical,
                    "offending_type": type(tool).__name__,
                },
            )

        canonical = tool.spec.id.canonical

        if canonical in seen:
            raise AgentConfigurationError(
                f"Duplicate tool id {canonical!r} in agent 'tools'.",
                details={"agent_id": spec.id.canonical, "tool_id": canonical},
            )

        seen.add(canonical)


def _validate_output_type(spec: AgentSpec) -> None:
    if spec.output_type is None:
        return

    if not isinstance(spec.output_type, type):
        raise AgentConfigurationError(
            "Agent 'output_type' must be a class or None.",
            details={
                "agent_id": spec.id.canonical,
                "output_type": repr(spec.output_type),
            },
        )


def _validate_max_iterations(spec: AgentSpec) -> None:
    if spec.max_iterations <= 0:
        raise AgentConfigurationError(
            "Agent 'max_iterations' must be a positive integer.",
            details={
                "agent_id": spec.id.canonical,
                "max_iterations": spec.max_iterations,
            },
        )


def _validate_system_prompt(spec: AgentSpec) -> None:
    if spec.system_prompt.strip():
        return

    warnings.warn(
        f"Agent {spec.id.canonical!r} was built with an empty system prompt.",
        EmptySystemPromptWarning,
        stacklevel=3,
    )
