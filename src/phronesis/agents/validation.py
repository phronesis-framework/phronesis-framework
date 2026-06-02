"""Eager validation of :class:`AgentSpec` at decoration time.

The :func:`agent` decorator invokes :func:`validate_spec` immediately
after building the spec so misconfiguration fails fast - before the
agent is registered or any run is attempted.

Validation is split into:

* Hard checks that raise :class:`AgentConfigurationError`:
    * ``model`` implements the :class:`LLMProvider` protocol.
    * every entry in ``tools`` is a :class:`Tool` instance.
    * tool ids are unique within the spec.
    * ``output_type`` is a class or ``None``.
    * ``max_iterations`` is a positive integer.
* Soft checks that emit a :class:`UserWarning` subclass instead of
  raising - currently only the empty-system-prompt warning.

Tool/provider feature compatibility is *not* checked here; that is
validated lazily on the first run.
"""

from __future__ import annotations

import warnings

from phronesis.agents.errors import AgentConfigurationError
from phronesis.agents.spec import AgentSpec
from phronesis.providers.protocol import LLMProvider
from phronesis.tools.tool import Tool


class EmptySystemPromptWarning(UserWarning):
    """Emitted when an agent is built with an empty or whitespace-only prompt.

    The warning is informational - the spec is still valid and the
    agent is still registered. Callers that prefer a strict policy can
    promote this warning to an error using :mod:`warnings.filterwarnings`.
    """


def validate_spec(spec: AgentSpec) -> None:
    """Run every eager structural check on ``spec``.

    The function returns ``None`` on success. Failures raise
    :class:`AgentConfigurationError` with structured ``details`` that
    identify the offending agent and field.

    Args:
        spec: The freshly built :class:`AgentSpec` to validate.

    Raises:
        AgentConfigurationError: if any structural rule fails (model
            type, tool type, duplicate tool id, output_type kind, or
            non-positive max_iterations).
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
