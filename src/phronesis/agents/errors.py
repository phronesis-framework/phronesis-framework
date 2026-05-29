"""Agent-side error hierarchy.

See ``docs/AGENTS-DECISIONS.md`` (D-11). These errors are surfaced to
the calling application — they are **not** serialized back to the LLM
(that role belongs to :class:`phronesis.tools.errors.ToolError`).

``AgentMaxIterationsError`` and ``AgentOutputValidationError`` are
native conditions raised by the loop and never wrap a cause.
``AgentConfigurationError`` is raised at spec-build time.
``AgentExecutionError`` wraps any non-``ToolError`` exception that
escapes a tool or provider call.
"""

from __future__ import annotations

from phronesis.errors import PhronesisError


class AgentError(PhronesisError):
    """Base class for every agent-raised error."""


class AgentMaxIterationsError(AgentError):
    """The agent loop reached ``max_iterations`` without finishing."""


class AgentOutputValidationError(AgentError):
    """Final output did not match ``output_type`` after the retry."""


class AgentConfigurationError(AgentError):
    """The agent spec is structurally invalid."""


class AgentExecutionError(AgentError):
    """An unhandled exception escaped the loop and aborted the run."""


class DuplicateAgentError(AgentConfigurationError):
    """Two distinct agents were registered under the same canonical id."""
