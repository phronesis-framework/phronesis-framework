"""Run-cycle data types for agents.

See ``docs/AGENTS-DECISIONS.md`` (D-05, D-06): a run is initiated with a
:class:`RunRequest` and produces a :class:`Result`. Both are frozen
dataclasses so they can be shared across threads, logged, or pickled.

:class:`RunId` is the stable identifier of a single execution and is
generated lazily by the loop. :class:`TokenUsage` is re-exported from
:mod:`phronesis.providers.usage` to keep callers from needing to import
provider internals.
"""

from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass, field
from types import MappingProxyType
from typing import Any, Final

from phronesis._internal.ids.generator import IdGenerator
from phronesis._internal.ids.id import Id
from phronesis.agents.errors import AgentError
from phronesis.communication.session_id import SessionId
from phronesis.core.messages import Message, ToolUseBlock
from phronesis.providers.usage import TokenUsage

__all__ = [
    "Result",
    "RunId",
    "RunRequest",
    "TokenUsage",
    "run_id_generator",
]

_EMPTY_METADATA: Final[Mapping[str, Any]] = MappingProxyType({})


class RunId(Id):
    """Stable identifier for one execution of an agent."""

    prefix = "RID"


run_id_generator: IdGenerator[RunId] = IdGenerator(RunId)
"""Singleton :class:`IdGenerator` for :class:`RunId`."""


@dataclass(frozen=True, slots=True)
class RunRequest:
    """Input to :meth:`phronesis.agents.Agent.run`.

    Attributes:
        input: The user-provided prompt that kicks off the run.
        session_id: Optional session linking this run with a multi-turn
            conversation.
        metadata: Free-form metadata propagated to instrumentation and
            available to tools via the runtime context.
        max_iterations: Per-run override of the agent's ``max_iterations``
            safety cap. ``None`` means use the spec default.
    """

    input: str
    session_id: SessionId | None = None
    metadata: Mapping[str, Any] = field(default_factory=lambda: _EMPTY_METADATA)
    max_iterations: int | None = None

    def __post_init__(self) -> None:
        if not isinstance(self.metadata, MappingProxyType):
            object.__setattr__(self, "metadata", MappingProxyType(dict(self.metadata)))


@dataclass(frozen=True, slots=True)
class Result:
    """Final outcome of an agent run.

    Attributes:
        run_id: The identifier the loop assigned to this run.
        output: Final output. A string for free-form runs, an instance of
            ``output_type`` for structured runs, or the error payload
            when ``success`` is ``False``.
        tokens: Aggregate token counts across every LLM call in the run.
        cost_usd: Estimated cost in USD if the caller plugged in pricing,
            otherwise ``None``.
        iterations: Number of loop iterations consumed.
        tool_calls: Every :class:`ToolUseBlock` the model emitted, in
            order. Results live in ``messages``.
        messages: Complete message history exchanged with the provider.
        success: ``True`` if the run reached a terminal answer, ``False``
            if it was aborted by an :class:`AgentError`.
        error: The :class:`AgentError` that aborted the run when
            ``success`` is ``False``.
    """

    run_id: RunId
    output: Any
    tokens: TokenUsage
    iterations: int
    tool_calls: tuple[ToolUseBlock, ...]
    messages: tuple[Message, ...]
    success: bool = True
    cost_usd: float | None = None
    error: AgentError | None = None
