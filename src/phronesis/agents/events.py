"""Streaming event types emitted by :meth:`Agent.stream`.

An agent run can be observed as an ordered stream of
:class:`AgentEvent` values. Every event is a frozen, slotted dataclass
so consumers can pattern-match against the union without worrying
about mutation or hidden state.

Event order for a successful run::

    RunStarted
      [ TextDelta* | ToolCallStarted -> ToolCallCompleted ]*
    RunCompleted

A run aborted by an :class:`AgentError` ends with :class:`RunFailed`
instead of :class:`RunCompleted`.

The :data:`AgentEvent` union is intentionally closed: adding a new
event type requires extending this module and updating every consumer.
"""

from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass, field
from types import MappingProxyType
from typing import Any, Final

from phronesis.agents.errors import AgentError
from phronesis.agents.id import AgentId
from phronesis.agents.run import Result, RunId
from phronesis.tools.tool_id import ToolId

_EMPTY_ARGS: Final[Mapping[str, Any]] = MappingProxyType({})


@dataclass(frozen=True, slots=True)
class RunStarted:
    """Emitted exactly once at the start of a run.

    Attributes:
        run_id: The :class:`RunId` the loop generated for this run.
        agent_id: The :class:`AgentId` of the agent being executed.
    """

    run_id: RunId
    agent_id: AgentId


@dataclass(frozen=True, slots=True)
class TextDelta:
    """A chunk of free-form assistant text streamed from the provider.

    Multiple ``TextDelta`` events may appear between tool-call pairs.
    Concatenating ``text`` in order reconstructs the assistant message.

    Attributes:
        text: The text fragment produced by the model.
    """

    text: str


@dataclass(frozen=True, slots=True)
class ToolCallStarted:
    """The model requested a tool invocation.

    Attributes:
        tool_call_id: Provider-assigned identifier that pairs this
            ``ToolCallStarted`` with its :class:`ToolCallCompleted`.
        tool_id: Canonical :class:`ToolId` of the tool being invoked.
        tool_name: LLM-facing name of the tool.
        args: Arguments the model produced for the tool call. Stored
            as a read-only :class:`MappingProxyType` so consumers
            cannot mutate them.
    """

    tool_call_id: str
    tool_id: ToolId
    tool_name: str
    args: Mapping[str, Any] = field(default_factory=lambda: _EMPTY_ARGS)

    def __post_init__(self) -> None:
        if not isinstance(self.args, MappingProxyType):
            object.__setattr__(self, "args", MappingProxyType(dict(self.args)))


@dataclass(frozen=True, slots=True)
class ToolCallCompleted:
    """A tool invocation finished, successfully or with a serialized error.

    A ``ToolError`` raised by the tool is captured here with
    ``is_error=True`` and ``result`` set to its serialized form (the
    same payload sent back to the model). Any other exception aborts
    the run before this event is emitted.

    Attributes:
        tool_call_id: Matches the id of the preceding
            :class:`ToolCallStarted`.
        result: Tool output, or the serialized error payload.
        is_error: ``True`` when ``result`` represents a ``ToolError``.
    """

    tool_call_id: str
    result: Any
    is_error: bool = False


@dataclass(frozen=True, slots=True)
class RunCompleted:
    """Emitted exactly once when the run reaches a terminal answer.

    Attributes:
        result: The same :class:`Result` returned by
            :meth:`Agent.run`.
    """

    result: Result


@dataclass(frozen=True, slots=True)
class RunFailed:
    """Emitted exactly once when the run is aborted by an :class:`AgentError`.

    Attributes:
        error: The error that caused the run to abort. Identical to
            the exception raised by :meth:`Agent.run`.
    """

    error: AgentError


AgentEvent = RunStarted | TextDelta | ToolCallStarted | ToolCallCompleted | RunCompleted | RunFailed
"""Closed union of every event a streaming run can emit.

Consumers should ``match`` against this union explicitly; adding a new
variant is a deliberate, breaking change.
"""
