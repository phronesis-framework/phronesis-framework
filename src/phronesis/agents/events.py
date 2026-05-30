"""Streaming event types emitted by :meth:`Agent.stream`.

See ``docs/AGENTS-DECISIONS.md`` (D-10): an agent run can be observed
as an ordered stream of :class:`AgentEvent` values. The union is closed
for the MVP — adding a new event type requires extending this module
and updating consumers explicitly.
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

__all__ = [
    "AgentEvent",
    "RunCompleted",
    "RunFailed",
    "RunStarted",
    "TextDelta",
    "ToolCallCompleted",
    "ToolCallStarted",
]

_EMPTY_ARGS: Final[Mapping[str, Any]] = MappingProxyType({})


@dataclass(frozen=True, slots=True)
class RunStarted:
    """Emitted once at the start of a run."""

    run_id: RunId
    agent_id: AgentId


@dataclass(frozen=True, slots=True)
class TextDelta:
    """A chunk of free-form text produced by the model."""

    text: str


@dataclass(frozen=True, slots=True)
class ToolCallStarted:
    """The model requested a tool invocation."""

    tool_call_id: str
    tool_id: ToolId
    tool_name: str
    args: Mapping[str, Any] = field(default_factory=lambda: _EMPTY_ARGS)

    def __post_init__(self) -> None:
        if not isinstance(self.args, MappingProxyType):
            object.__setattr__(self, "args", MappingProxyType(dict(self.args)))


@dataclass(frozen=True, slots=True)
class ToolCallCompleted:
    """A tool invocation finished, successfully or with a serialized error."""

    tool_call_id: str
    result: Any
    is_error: bool = False


@dataclass(frozen=True, slots=True)
class RunCompleted:
    """Emitted once when the run reaches a terminal answer."""

    result: Result


@dataclass(frozen=True, slots=True)
class RunFailed:
    """Emitted once when the run is aborted by an :class:`AgentError`."""

    error: AgentError


AgentEvent = RunStarted | TextDelta | ToolCallStarted | ToolCallCompleted | RunCompleted | RunFailed
"""Union of every event a run can emit."""
