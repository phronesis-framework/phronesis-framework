"""Per-call execution :class:`Context` injected into tools by type.

A frozen, immutable record carrying trace and session identifiers,
arbitrary metadata and an optional logger. Tools declare a parameter
typed ``Context`` and the framework injects the current instance at
invocation time; callers never construct one for tool calls explicitly.
"""

from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass, field
from datetime import datetime
from logging import Logger, LoggerAdapter
from types import MappingProxyType
from typing import TYPE_CHECKING, Any, Final

from phronesis.context.budget import Budget

if TYPE_CHECKING:
    from phronesis.agents.id import AgentId
    from phronesis.agents.run import RunId
    from phronesis.communication.session_id import SessionId

_EMPTY_METADATA: Final[Mapping[str, Any]] = MappingProxyType({})


@dataclass(frozen=True, slots=True)
class Context:
    """Read-only execution context for a tool invocation.

    Constructed by the runtime, never by the tool itself. All fields are
    optional so partial fixtures are cheap to build.

    ``trace_id`` is intentionally typed as ``str``: it follows the
    OpenTelemetry specification, not the framework's identity system.
    """

    run_id: RunId | None = None
    agent_id: AgentId | None = None
    session_id: SessionId | None = None
    trace_id: str | None = None
    logger: Logger | LoggerAdapter[Any] | None = None
    budget: Budget | None = None
    deadline: datetime | None = None
    metadata: Mapping[str, Any] = field(default_factory=lambda: _EMPTY_METADATA)

    def __post_init__(self) -> None:
        if not isinstance(self.metadata, MappingProxyType):
            object.__setattr__(self, "metadata", MappingProxyType(dict(self.metadata)))
