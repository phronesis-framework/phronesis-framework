"""Executable agent wrapper.

:class:`Agent` is the callable side of an agent declaration; the
pure-data side lives on :attr:`Agent.spec` as an :class:`AgentSpec`.
The wrapper carries no extra state beyond the spec — identity, name
and every configurable property are read straight from it.

Use :meth:`Agent.run` for a one-shot call and :meth:`Agent.session`
to open a stateful multi-turn conversation backed by the same spec.

Use the :meth:`Agent.with_provider`, :meth:`Agent.with_tools`,
:meth:`Agent.with_system_prompt`, :meth:`Agent.with_max_iterations`,
:meth:`Agent.with_context_builder`, :meth:`Agent.with_output_type` and
:meth:`Agent.with_description` methods to derive a new agent with a
single field swapped. They preserve immutability — the receiver agent
is never mutated.
"""

from __future__ import annotations

import dataclasses
from collections.abc import Sequence

from phronesis.agents.id import AgentId
from phronesis.agents.loop import run_loop
from phronesis.agents.run import Result, RunRequest
from phronesis.agents.session import Session
from phronesis.agents.spec import AgentSpec
from phronesis.communication.session_id import SessionId
from phronesis.context.protocol import ContextBuilder
from phronesis.providers.protocol import LLMProvider
from phronesis.tools.tool import Tool


class Agent:
    """Callable wrapper around an :class:`AgentSpec`.

    The spec is the source of truth; the wrapper holds no additional
    configuration. ``__slots__`` is used so an :class:`Agent` is a
    fixed-shape object suitable for very wide registries.

    Attributes:
        spec: The :class:`AgentSpec` this agent executes.
    """

    __slots__ = ("spec",)

    def __init__(self, spec: AgentSpec) -> None:
        """Bind ``spec`` to this agent.

        Args:
            spec: A pre-validated :class:`AgentSpec`. The wrapper does
                not re-validate the spec; the :func:`agent` decorator
                runs :func:`validate_spec` before constructing the
                wrapper.
        """
        self.spec = spec

    @property
    def id(self) -> AgentId:
        """Canonical :class:`AgentId` of the underlying spec."""
        return self.spec.id

    @property
    def name(self) -> str:
        """LLM-facing name of the agent (from :attr:`AgentSpec.name`)."""
        return self.spec.name

    async def run(self, input_or_request: str | RunRequest) -> Result:
        """Execute the tool-calling loop and return the final :class:`Result`.

        Args:
            input_or_request: Either a free-form string, which is
                wrapped in a default :class:`RunRequest`, or an
                explicit :class:`RunRequest` for callers that need to
                set ``metadata``, ``max_iterations`` or ``session_id``.

        Returns:
            The :class:`Result` produced by the loop.

        Raises:
            AgentMaxIterationsError: if the loop hits
                :attr:`AgentSpec.max_iterations` without finishing.
            AgentExecutionError: if any non-``ToolError`` exception
                escapes a tool or provider call.
        """
        request = (
            input_or_request
            if isinstance(input_or_request, RunRequest)
            else RunRequest(input=input_or_request)
        )

        return await run_loop(self.spec, request)

    def session(self, session_id: SessionId | None = None) -> Session:
        """Open a multi-turn :class:`Session` bound to this agent.

        Args:
            session_id: Optional id to attach to the session. When
                omitted, the session mints a new :class:`SessionId`.

        Returns:
            A fresh :class:`Session` with an empty message history.
        """
        return Session(self.spec, session_id=session_id)

    def with_provider(self, provider: LLMProvider) -> Agent:
        """Return a copy of this agent backed by ``provider``.

        Args:
            provider: An :class:`LLMProvider` implementation that
                replaces :attr:`AgentSpec.model` in the derived spec.

        Returns:
            A new :class:`Agent` sharing every other field with this
            one. The receiver is not mutated.
        """
        return Agent(dataclasses.replace(self.spec, model=provider))

    def with_tools(self, tools: Sequence[Tool]) -> Agent:
        """Return a copy of this agent whose tools are ``tools``.

        The replacement is total: the new spec carries exactly the
        passed sequence. Use :meth:`with_added_tools` to extend
        instead.

        Args:
            tools: Sequence of :class:`Tool` instances to set as the
                full tool list of the derived spec.

        Returns:
            A new :class:`Agent` with the requested tool tuple.
        """
        return Agent(dataclasses.replace(self.spec, tools=tuple(tools)))

    def with_added_tools(self, tools: Sequence[Tool]) -> Agent:
        """Return a copy of this agent with ``tools`` appended.

        Args:
            tools: Sequence of :class:`Tool` instances to append to
                the current tool tuple.

        Returns:
            A new :class:`Agent` whose tools are the original tuple
            followed by ``tools``.
        """
        merged = (*self.spec.tools, *tools)

        return Agent(dataclasses.replace(self.spec, tools=merged))

    def with_system_prompt(self, system_prompt: str) -> Agent:
        """Return a copy of this agent with a new system prompt.

        Args:
            system_prompt: Plain-text instructions sent on every turn
                of the derived agent.

        Returns:
            A new :class:`Agent` with the updated prompt.
        """
        return Agent(dataclasses.replace(self.spec, system_prompt=system_prompt))

    def with_max_iterations(self, max_iterations: int) -> Agent:
        """Return a copy of this agent with a new iteration cap.

        Args:
            max_iterations: Upper bound on tool-calling loop
                iterations of the derived agent. Must be positive;
                the loop validates this when the derived agent runs.

        Returns:
            A new :class:`Agent` with the updated cap.
        """
        return Agent(dataclasses.replace(self.spec, max_iterations=max_iterations))

    def with_context_builder(self, context_builder: ContextBuilder) -> Agent:
        """Return a copy of this agent with a new :class:`ContextBuilder`.

        Args:
            context_builder: The builder the derived agent will use to
                assemble provider-facing message lists.

        Returns:
            A new :class:`Agent` with the updated builder.
        """
        return Agent(dataclasses.replace(self.spec, context_builder=context_builder))

    def with_output_type(self, output_type: type | None) -> Agent:
        """Return a copy of this agent with a new ``output_type``.

        Args:
            output_type: Expected output class for structured runs,
                or ``None`` for free-form text.

        Returns:
            A new :class:`Agent` with the updated output type.
        """
        return Agent(dataclasses.replace(self.spec, output_type=output_type))

    def with_description(self, description: str) -> Agent:
        """Return a copy of this agent with a new description.

        Args:
            description: Free-form human-readable summary stored on
                the derived spec.

        Returns:
            A new :class:`Agent` with the updated description.
        """
        return Agent(dataclasses.replace(self.spec, description=description))

    def describe(self) -> str:
        """Return a multi-line human-readable summary of this agent.

        The summary is intended for REPL / log inspection. It is not
        a stable serialization format.

        Returns:
            A string with one line per significant spec field,
            including model class name, tool names, builder class
            name and the iteration cap.
        """
        spec = self.spec
        tool_names = ", ".join(t.spec.name for t in spec.tools) or "<none>"
        builder_name = type(spec.context_builder).__name__
        model_name = type(spec.model).__name__
        output_name = spec.output_type.__name__ if spec.output_type is not None else "<free-form>"
        prompt_preview = _preview(spec.system_prompt, limit=80)
        description = spec.description.strip() or "<no description>"

        return (
            f"Agent[{spec.name}] (id={spec.id.canonical})\n"
            f"  version: {spec.version}\n"
            f"  description: {description}\n"
            f"  model: {model_name}\n"
            f"  system_prompt: {prompt_preview}\n"
            f"  tools: {tool_names}\n"
            f"  context_builder: {builder_name}\n"
            f"  output_type: {output_name}\n"
            f"  max_iterations: {spec.max_iterations}"
        )

    def __repr__(self) -> str:
        return f"Agent(id={self.spec.id.canonical!r}, name={self.spec.name!r})"


def _preview(text: str, *, limit: int) -> str:
    collapsed = " ".join(text.split())

    if len(collapsed) <= limit:
        return repr(collapsed)

    return repr(collapsed[: limit - 1] + "\u2026")
