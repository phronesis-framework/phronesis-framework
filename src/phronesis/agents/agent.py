"""Executable agent wrapper.

:class:`Agent` is the callable side of an agent declaration; the
pure-data side lives on :attr:`Agent.spec` as an :class:`AgentSpec`.
The wrapper carries no extra state beyond the spec — identity, name
and every configurable property are read straight from it.

Use :meth:`Agent.run` for a one-shot call and :meth:`Agent.session`
to open a stateful multi-turn conversation backed by the same spec.
"""

from __future__ import annotations

from phronesis.agents.id import AgentId
from phronesis.agents.loop import run_loop
from phronesis.agents.run import Result, RunRequest
from phronesis.agents.session import Session
from phronesis.agents.spec import AgentSpec
from phronesis.communication.session_id import SessionId


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

    def __repr__(self) -> str:
        return f"Agent(id={self.spec.id.canonical!r}, name={self.spec.name!r})"
