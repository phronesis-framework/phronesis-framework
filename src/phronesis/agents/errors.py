"""Agent-side error hierarchy.

Every error in this module is intended for the *caller* of the agent.
They are raised out of :meth:`Agent.run` (and :func:`run_loop`) and are
not serialized back to the LLM - tool-level failures use
:class:`phronesis.tools.errors.ToolError`, which the loop converts into
a ``ToolResultBlock`` with ``is_error=True``.

The hierarchy:

* :class:`AgentError` - common base, subclass of :class:`PhronesisError`.
* :class:`AgentMaxIterationsError` - the loop hit the iteration cap.
  Raised natively by the loop; never wraps a cause.
* :class:`AgentOutputValidationError` - structured output did not match
  the declared ``output_type``. Native to the validator.
* :class:`AgentConfigurationError` - raised at spec-build time when the
  spec is structurally invalid.
* :class:`AgentExecutionError` - wraps any non-``ToolError`` exception
  that escapes a tool or provider call.
* :class:`DuplicateAgentError` - subclass of the configuration error
  for the registry-collision case.
"""

from __future__ import annotations

from phronesis.errors import PhronesisError


class AgentError(PhronesisError):
    """Base class for every agent-raised error.

    Subclasses inherit the ``details`` payload of
    :class:`PhronesisError`, which carries structured diagnostic data
    (agent id, max_iterations, tool name, etc.) suitable for logging.
    """


class AgentMaxIterationsError(AgentError):
    """The tool-calling loop hit ``max_iterations`` before terminating.

    Raised by :func:`phronesis.agents.loop.run_loop` when the model
    keeps requesting tool calls past the configured cap. ``details``
    contains ``agent_id`` and ``max_iterations``.
    """


class AgentOutputValidationError(AgentError):
    """The final output did not match the declared ``output_type``.

    Raised by the structured-output validator after the configured
    retry attempt has been consumed.
    """


class AgentConfigurationError(AgentError):
    """The :class:`AgentSpec` is structurally invalid.

    Raised eagerly by :func:`phronesis.agents.validation.validate_spec`
    when, for example, ``model`` does not implement
    :class:`LLMProvider`, ``tools`` contains a duplicate id, or
    ``max_iterations`` is not a positive integer.
    """


class AgentExecutionError(AgentError):
    """An unhandled exception escaped the loop and aborted the run.

    Wraps any exception that is **not** a
    :class:`phronesis.tools.errors.ToolError` and that escapes a
    provider call or a tool invocation. The original exception is
    available via ``__cause__``.
    """


class DuplicateAgentError(AgentConfigurationError):
    """Two distinct agents were registered under the same canonical id.

    Raised by the agent registry when ``register`` is called with an id
    that is already taken by a *different* :class:`Agent` instance.
    Re-registering the same instance is a no-op.
    """


class AgentBudgetExceededError(AgentError):
    """The run consumed more than the budget allotted by the caller.

    Raised by :func:`phronesis.agents.loop.run_loop` when the
    aggregated token count, cost or elapsed time exceeds the bound
    declared on :class:`RunRequest`. ``details`` carries the limit
    name, its threshold, and the observed value.
    """


class AgentTimeoutError(AgentBudgetExceededError):
    """The run exceeded :attr:`RunRequest.timeout_seconds`.

    Specialisation of :class:`AgentBudgetExceededError` for the time
    dimension. The ``__cause__`` may be :class:`asyncio.TimeoutError`
    when the loop was cancelled by ``asyncio.wait_for``.
    """
