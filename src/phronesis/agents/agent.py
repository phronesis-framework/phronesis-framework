"""Executable agent wrapper.

See ``docs/AGENTS-DECISIONS.md`` (D-02, D-09): :class:`Agent` is the
callable side of an agent declaration; ``agent.spec`` is the pure-data
side. ``run()`` and ``stream()`` are implemented in later phases (loop,
streaming, session) and intentionally raise here so the registry can
hold a working :class:`Agent` from day one.
"""

from __future__ import annotations

from phronesis.agents.id import AgentId
from phronesis.agents.loop import run_loop
from phronesis.agents.run import Result, RunRequest
from phronesis.agents.session import Session
from phronesis.agents.spec import AgentSpec
from phronesis.communication.session_id import SessionId


class Agent:
    """Callable wrapper exposing an :class:`AgentSpec`.

    The spec is treated as the source of truth; the wrapper holds no
    additional configuration of its own. Identity is the spec's id.
    """

    __slots__ = ("spec",)

    def __init__(self, spec: AgentSpec) -> None:
        self.spec = spec

    @property
    def id(self) -> AgentId:
        """Stable identifier of the underlying :class:`AgentSpec`."""
        return self.spec.id

    @property
    def name(self) -> str:
        """LLM-facing name of the agent."""
        return self.spec.name

    async def run(self, input_or_request: str | RunRequest) -> Result:
        """Execute the tool-calling loop and return the final :class:`Result`.

        Accepts either a free-form string (wrapped in a default
        :class:`RunRequest`) or an explicit request object.
        """
        request = (
            input_or_request
            if isinstance(input_or_request, RunRequest)
            else RunRequest(input=input_or_request)
        )

        return await run_loop(self.spec, request)

    def session(self, session_id: SessionId | None = None) -> Session:
        """Open a multi-turn :class:`Session` bound to this agent."""
        return Session(self.spec, session_id=session_id)

    def __repr__(self) -> str:
        return f"Agent(id={self.spec.id.canonical!r}, name={self.spec.name!r})"
