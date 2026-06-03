"""Runtime orchestration layer.

This package exposes the building blocks used by pipelines, supervisors
and RAG flows to compose agents and async callables into higher-level
execution graphs:

* :class:`Executable` is the single contract every node satisfies.
* :class:`ExecutionContext` carries run-scoped state (ids, deadline,
  cancellation, metadata, logger).
* :class:`RunOutcome` normalises every node's return value.
* :func:`as_node`, :func:`agent_node`, :func:`callable_node` adapt
  :class:`phronesis.agents.Agent` instances and async callables to the
  :class:`Executable` protocol.

Nineteen modes are exported - from primitive composition
(:class:`Sequence`, :class:`Parallel`, :class:`Race`) to cognitive
patterns (:class:`Reflexion`, :class:`TreeSearch`, :class:`PlanAndExecute`).

All errors raised by the package inherit from
:class:`RuntimeOrchestrationError`.
"""

from __future__ import annotations

from phronesis.runtime.context import ExecutionContext, RunId
from phronesis.runtime.errors import (
    ApprovalDeniedError,
    ApprovalTimeoutError,
    CancelledError,
    ConsensusError,
    ExecutionFailedError,
    HandoffLimitError,
    LoopExhaustedError,
    NoMatchingRouteError,
    RuntimeOrchestrationError,
    ValidationFailedError,
)
from phronesis.runtime.modes.approval import Approval
from phronesis.runtime.modes.cascade import Cascade
from phronesis.runtime.modes.conditional import Conditional
from phronesis.runtime.modes.consensus import Consensus
from phronesis.runtime.modes.debate import Debate
from phronesis.runtime.modes.fallback import Fallback
from phronesis.runtime.modes.handoff_chain import HandoffChain
from phronesis.runtime.modes.loop import Loop
from phronesis.runtime.modes.map_reduce import MapReduce
from phronesis.runtime.modes.parallel import Parallel
from phronesis.runtime.modes.plan_and_execute import PlanAndExecute
from phronesis.runtime.modes.race import Race
from phronesis.runtime.modes.reflexion import Reflexion
from phronesis.runtime.modes.retry import Retry
from phronesis.runtime.modes.router import Router
from phronesis.runtime.modes.sequence import Sequence
from phronesis.runtime.modes.supervisor import Supervisor
from phronesis.runtime.modes.tree_search import TreeSearch
from phronesis.runtime.modes.validation import Validation, ValidationResult
from phronesis.runtime.node import agent_node, as_node, callable_node
from phronesis.runtime.outcome import RunOutcome
from phronesis.runtime.protocol import Executable

__all__ = [
    "Approval",
    "ApprovalDeniedError",
    "ApprovalTimeoutError",
    "CancelledError",
    "Cascade",
    "Conditional",
    "Consensus",
    "ConsensusError",
    "Debate",
    "Executable",
    "ExecutionContext",
    "ExecutionFailedError",
    "Fallback",
    "HandoffChain",
    "HandoffLimitError",
    "Loop",
    "LoopExhaustedError",
    "MapReduce",
    "NoMatchingRouteError",
    "Parallel",
    "PlanAndExecute",
    "Race",
    "Reflexion",
    "Retry",
    "Router",
    "RunId",
    "RunOutcome",
    "RuntimeOrchestrationError",
    "Sequence",
    "Supervisor",
    "TreeSearch",
    "Validation",
    "ValidationFailedError",
    "ValidationResult",
    "agent_node",
    "as_node",
    "callable_node",
]
