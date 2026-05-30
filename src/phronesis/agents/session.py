"""Stateful multi-turn session over a stateless :class:`Agent`.

See ``docs/AGENTS-DECISIONS.md`` (D-09): the agent itself is stateless;
conversation state lives in :class:`Session`. Each call to
:meth:`Session.run` appends the user input to the running history,
delegates to :func:`run_loop`, and stores the returned message tuple as
the new baseline for the next turn.
"""

from __future__ import annotations

import uuid

from phronesis.agents.loop import run_loop
from phronesis.agents.run import Result, RunRequest
from phronesis.agents.spec import AgentSpec
from phronesis.communication.session_id import SessionId, session_id_generator
from phronesis.core.messages import Message


def _new_session_id() -> SessionId:
    return session_id_generator.from_canonical(
        f"phronesis.communication.session.s{uuid.uuid4().hex[:12]}",
    )


class Session:
    """Multi-turn wrapper around a stateless agent.

    Attributes:
        id: The stable :class:`SessionId` for this conversation.
    """

    __slots__ = ("_messages", "_spec", "id")

    def __init__(self, spec: AgentSpec, session_id: SessionId | None = None) -> None:
        self._spec = spec
        self.id: SessionId = session_id if session_id is not None else _new_session_id()
        self._messages: tuple[Message, ...] = ()

    @property
    def messages(self) -> tuple[Message, ...]:
        """Snapshot of every message exchanged so far."""
        return self._messages

    async def run(self, input_or_request: str | RunRequest) -> Result:
        """Run one turn, continuing from the accumulated history.

        Accepts either a free-form string (wrapped in a default
        :class:`RunRequest` bound to this session) or an explicit
        :class:`RunRequest`. The session id on the request is always
        forced to this session's id.
        """
        request = self._coerce_request(input_or_request)

        if self._messages:
            result = await run_loop(self._spec, request, initial_history=self._messages)
        else:
            result = await run_loop(self._spec, request)

        self._messages = result.messages

        return result

    def reset(self) -> None:
        """Drop the conversation history but keep the same session id."""
        self._messages = ()

    def _coerce_request(self, input_or_request: str | RunRequest) -> RunRequest:
        if isinstance(input_or_request, RunRequest):
            return RunRequest(
                input=input_or_request.input,
                session_id=self.id,
                metadata=input_or_request.metadata,
                max_iterations=input_or_request.max_iterations,
            )

        return RunRequest(input=input_or_request, session_id=self.id)

    def __repr__(self) -> str:
        return f"Session(id={self.id.canonical!r}, agent={self._spec.id.canonical!r})"
