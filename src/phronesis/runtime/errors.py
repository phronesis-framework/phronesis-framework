"""Error hierarchy for the :mod:`phronesis.runtime` package.

All runtime orchestration failures inherit from
:class:`RuntimeOrchestrationError`, which extends
:class:`phronesis.errors.PhronesisError`. Each subclass carries a stable
``code`` attribute mirroring the style used by
:class:`phronesis.memory.errors.MemoryError`.

The hierarchy is flat on purpose: each concrete error names a specific
failure mode that callers may want to react to (loop exhausted, no
matching route, approval denied, ...). New errors should be added here
rather than in individual mode modules.
"""

from __future__ import annotations

from phronesis.errors import PhronesisError


class RuntimeOrchestrationError(PhronesisError):
    """Base class for every failure originating in :mod:`phronesis.runtime`."""

    code: str = "runtime_error"


class ExecutionFailedError(RuntimeOrchestrationError):
    """A node finished with ``success=False`` and the mode could not recover."""

    code = "runtime_execution_failed"


class LoopExhaustedError(RuntimeOrchestrationError):
    """A loop-shaped mode reached ``max_iterations`` without satisfying its predicate."""

    code = "runtime_loop_exhausted"


class HandoffLimitError(RuntimeOrchestrationError):
    """A handoff chain reached ``max_handoffs`` without terminating."""

    code = "runtime_handoff_limit"


class NoMatchingRouteError(RuntimeOrchestrationError):
    """Router classifier produced a key with no matching route and no default."""

    code = "runtime_no_matching_route"


class ConsensusError(RuntimeOrchestrationError):
    """Voters in a consensus mode failed to reach ``min_agreement``."""

    code = "runtime_no_consensus"


class ValidationFailedError(RuntimeOrchestrationError):
    """Validator rejected every attempt before ``max_attempts`` ran out."""

    code = "runtime_validation_failed"


class ApprovalDeniedError(RuntimeOrchestrationError):
    """The approval callback returned ``False`` for the produced output."""

    code = "runtime_approval_denied"


class ApprovalTimeoutError(RuntimeOrchestrationError):
    """The approval callback did not produce a verdict before ``timeout_s``."""

    code = "runtime_approval_timeout"


class CancelledError(RuntimeOrchestrationError):
    """A run was cancelled cooperatively via :attr:`ExecutionContext.cancellation`."""

    code = "runtime_cancelled"
