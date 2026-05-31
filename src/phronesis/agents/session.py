"""Stateful multi-turn session over a stateless :class:`Agent`.

An :class:`Agent` is stateless: every :meth:`Agent.run` call starts
from a fresh history. :class:`Session` adds the missing piece —
conversation memory — without coupling the spec to it.

Each :meth:`Session.run` call:

1. Coerces the input into a :class:`RunRequest` bound to the session
   id.
2. Calls :func:`run_loop`, passing the accumulated history as
   ``initial_history`` (or seeding a fresh history on the first turn).
3. Stores the returned :attr:`Result.messages` as the new baseline.

Sessions are not safe for concurrent use — each turn mutates the
internal history; serialize calls per session if needed.
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

    The session owns the conversation history. It does not own the
    spec — multiple sessions can share the same :class:`AgentSpec`
    safely because the spec is immutable.

    Attributes:
        id: The stable :class:`SessionId` for this conversation.
    """

    __slots__ = ("_messages", "_spec", "id")

    def __init__(self, spec: AgentSpec, session_id: SessionId | None = None) -> None:
        """Create a session bound to ``spec``.

        Args:
            spec: The :class:`AgentSpec` whose loop and tools will run
                on every turn.
            session_id: Existing :class:`SessionId` to attach to this
                conversation. When ``None``, a new id is generated.
        """
        self._spec = spec
        self.id: SessionId = session_id if session_id is not None else _new_session_id()
        self._messages: tuple[Message, ...] = ()

    @property
    def messages(self) -> tuple[Message, ...]:
        """Read-only snapshot of every :class:`Message` exchanged so far."""
        return self._messages

    async def run(self, input_or_request: str | RunRequest) -> Result:
        """Run one turn, continuing from the accumulated history.

        On the first call the loop seeds a fresh ``system + user``
        history; on later calls it appends a new ``user`` message to
        the stored history. The returned :attr:`Result.messages`
        becomes the baseline for the next turn.

        Args:
            input_or_request: Either a free-form string (wrapped in a
                default :class:`RunRequest`) or an explicit request.
                The session id is always overridden with this
                session's id.

        Returns:
            The :class:`Result` produced by :func:`run_loop`.

        Raises:
            AgentMaxIterationsError: if the loop hits the iteration
                cap without finishing.
            AgentExecutionError: if a tool or provider call raises a
                non-``ToolError`` exception.
        """
        request = self._coerce_request(input_or_request)

        if self._messages:
            result = await run_loop(self._spec, request, initial_history=self._messages)
        else:
            result = await run_loop(self._spec, request)

        self._messages = result.messages

        return result

    def reset(self) -> None:
        """Clear the conversation history, keeping the same session id.

        Subsequent calls to :meth:`run` behave as if this were the
        first turn. The :attr:`id` attribute is preserved so external
        consumers can keep using it as a stable handle.
        """
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
