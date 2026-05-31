"""Run-cycle data types for agents.

A run is initiated with a :class:`RunRequest` and produces a
:class:`Result`. Both types are frozen dataclasses so they can be
shared across threads, logged, or pickled without surprises.

* :class:`RunId` is the stable identifier of a single execution. The
  loop generates one per call via the singleton
  :data:`run_id_generator`.
* :class:`TokenUsage` is re-exported from
  :mod:`phronesis.providers.usage` so callers never need to reach
  into the provider package directly.
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
from phronesis.providers.usage import TokenUsage as TokenUsage

_EMPTY_METADATA: Final[Mapping[str, Any]] = MappingProxyType({})


class RunId(Id):
    """Stable identifier for one execution of an agent.

    Subclass of :class:`phronesis._internal.ids.id.Id` with the short
    prefix ``"RID"``. The canonical form looks like
    ``phronesis.runtime.run.r<hex>``.
    """

    prefix = "RID"


run_id_generator: IdGenerator[RunId] = IdGenerator(RunId)
"""Process-wide :class:`IdGenerator` bound to :class:`RunId`.

The loop uses this generator to mint a new id for every run via
``run_id_generator.from_canonical(...)``.
"""


@dataclass(frozen=True, slots=True)
class RunRequest:
    """Input to :meth:`phronesis.agents.Agent.run`.

    A request is a frozen value object; the loop never mutates it.
    Metadata is coerced to a read-only :class:`MappingProxyType` in
    ``__post_init__`` so a caller cannot mutate it after construction.

    Attributes:
        input: The user-provided prompt that kicks off the run.
        session_id: Optional :class:`SessionId` linking this run with
            a multi-turn conversation. Used by
            :class:`phronesis.agents.session.Session` to thread runs
            together and as an attribute on emitted spans/metrics.
        metadata: Free-form mapping propagated to instrumentation and
            exposed to tools through the runtime
            :class:`phronesis.context.context.Context`.
        max_iterations: Per-run override of
            :attr:`AgentSpec.max_iterations`. ``None`` means use the
            value from the spec.
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

    Returned by :meth:`Agent.run` and yielded as the payload of
    :class:`phronesis.agents.events.RunCompleted` events. Frozen so it
    can be shared and serialized safely.

    Attributes:
        run_id: The :class:`RunId` the loop assigned to this run.
        output: Final output. A string for free-form runs, an instance
            of ``output_type`` for structured runs, or the serialized
            error payload when ``success`` is ``False``.
        tokens: Aggregate :class:`TokenUsage` across every LLM call in
            the run.
        iterations: Number of tool-calling loop iterations consumed.
        tool_calls: Every :class:`ToolUseBlock` the model emitted,
            in the order they were requested. Tool results live in
            ``messages``.
        messages: Complete tuple of :class:`Message` exchanged with
            the provider during the run.
        success: ``True`` if the run reached a terminal answer,
            ``False`` if it was aborted by an :class:`AgentError`.
        cost_usd: Estimated cost in USD if the caller plugged in
            pricing, otherwise ``None``.
        error: The :class:`AgentError` that aborted the run when
            ``success`` is ``False``; ``None`` for successful runs.
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
