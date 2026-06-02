"""Tests for runtime error hierarchy."""

from __future__ import annotations

from phronesis.errors import PhronesisError
from phronesis.runtime import (
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


class TestErrors:
    def test_all_descend_from_runtime_error(self) -> None:
        subclasses = (
            ExecutionFailedError,
            LoopExhaustedError,
            HandoffLimitError,
            NoMatchingRouteError,
            ConsensusError,
            ValidationFailedError,
            ApprovalDeniedError,
            ApprovalTimeoutError,
            CancelledError,
        )

        for cls in subclasses:
            assert issubclass(cls, RuntimeOrchestrationError)

    def test_runtime_error_is_phronesis_error(self) -> None:
        assert issubclass(RuntimeOrchestrationError, PhronesisError)

    def test_codes_are_unique(self) -> None:
        codes = {
            RuntimeOrchestrationError.code,
            ExecutionFailedError.code,
            LoopExhaustedError.code,
            HandoffLimitError.code,
            NoMatchingRouteError.code,
            ConsensusError.code,
            ValidationFailedError.code,
            ApprovalDeniedError.code,
            ApprovalTimeoutError.code,
            CancelledError.code,
        }

        assert len(codes) == 10

    def test_details_propagate(self) -> None:
        err = NoMatchingRouteError("no route", details={"route": "x"})

        assert err.details["route"] == "x"
