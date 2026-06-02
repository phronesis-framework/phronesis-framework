"""Pure data spec for a declared agent.

:class:`AgentSpec` is the source of truth for every configurable
property of an agent. It is a frozen dataclass with no behaviour of
its own - executing the spec is the job of
:class:`phronesis.agents.agent.Agent` and the loop in
:mod:`phronesis.agents.loop`.

The spec carries a reference to the :class:`LLMProvider` because
providers are typically long-lived objects shared across multiple
agents, and storing the reference here lets the loop avoid a separate
provider-lookup step.
"""

from __future__ import annotations

from dataclasses import dataclass, field

from phronesis.agents.hooks import AgentHooks
from phronesis.agents.id import AgentId
from phronesis.context.default import DefaultContextBuilder
from phronesis.context.protocol import ContextBuilder
from phronesis.providers.protocol import LLMProvider
from phronesis.tools.tool import Tool

_DEFAULT_CONTEXT_BUILDER: ContextBuilder = DefaultContextBuilder()
_DEFAULT_HOOKS: AgentHooks = AgentHooks()


@dataclass(frozen=True, slots=True)
class AgentSpec:
    """Static, frozen description of an agent.

    Instances are immutable and safe to share across threads or async
    tasks. They are validated eagerly by
    :func:`phronesis.agents.validation.validate_spec` whenever they are
    constructed through the :func:`agent` decorator.

    Attributes:
        id: Stable :class:`AgentId` used for registry lookup and
            observability attribute values.
        name: LLM-facing name used in tool-calling and multi-agent
            discovery payloads.
        model: :class:`LLMProvider` instance that backs every call to
            :meth:`Agent.run` and :meth:`Agent.stream`.
        system_prompt: Plain-text system instructions sent on every
            turn. May be empty, in which case
            :class:`EmptySystemPromptWarning` is emitted at validation
            time.
        tools: Tuple of :class:`Tool` instances the agent may invoke.
            May be empty for tool-less agents. Duplicate tool ids are
            rejected by :func:`validate_spec`.
        description: Free-form human-readable summary. Defaults to the
            empty string.
        output_type: Expected output type for structured runs. ``None``
            means the agent returns free-form text.
        max_iterations: Upper bound on tool-calling loop iterations.
            When the loop reaches this cap without a terminal answer
            it raises :class:`AgentMaxIterationsError`. Must be > 0.
        version: Free-form version string, defaulting to ``"0.1.0"``.
        context_builder: :class:`ContextBuilder` instance the loop
            invokes on every iteration to assemble the provider-facing
            message list. The :func:`agent` decorator injects a shared
            :class:`DefaultContextBuilder` singleton when the caller
            does not override it.
        hooks: :class:`AgentHooks` aggregate of optional lifecycle
            callbacks. Defaults to an :class:`AgentHooks` instance
            with every field unset.
    """

    id: AgentId
    name: str
    model: LLMProvider
    system_prompt: str
    tools: tuple[Tool, ...] = ()
    description: str = ""
    output_type: type | None = None
    max_iterations: int = 20
    version: str = "0.1.0"
    context_builder: ContextBuilder = field(default=_DEFAULT_CONTEXT_BUILDER)
    hooks: AgentHooks = field(default=_DEFAULT_HOOKS)

    def __repr__(self) -> str:
        return (
            f"AgentSpec(id={self.id.canonical!r}, name={self.name!r}, "
            f"model={type(self.model).__name__}, tools={len(self.tools)}, "
            f"max_iterations={self.max_iterations}, version={self.version!r})"
        )
