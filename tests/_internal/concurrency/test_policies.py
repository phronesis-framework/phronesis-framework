"""Tests for gather policies."""

from __future__ import annotations

import pytest

from phronesis._internal.concurrency import (
    BestEffortPolicy,
    FailFastPolicy,
    PartialFailureError,
)


class TestFailFastPolicy:
    def test_return_exceptions_is_false(self) -> None:
        assert FailFastPolicy().return_exceptions is False

    def test_reconcile_passes_results_through(self) -> None:
        policy = FailFastPolicy()

        out = policy.reconcile([1, 2, 3])

        assert out == [1, 2, 3]


class TestBestEffortPolicy:
    def test_return_exceptions_is_true(self) -> None:
        assert BestEffortPolicy().return_exceptions is True

    def test_reconcile_returns_results_when_no_failures(self) -> None:
        policy = BestEffortPolicy()

        out = policy.reconcile(["a", "b", "c"])

        assert out == ["a", "b", "c"]

    def test_reconcile_raises_partial_failure_when_any_failed(self) -> None:
        policy = BestEffortPolicy()
        boom = RuntimeError("boom")

        with pytest.raises(PartialFailureError) as info:
            policy.reconcile([1, boom, 3])

        exc = info.value

        assert exc.failed_count == 1
        assert exc.successful_count == 2
        assert exc.results == [1, None, 3]
        assert exc.exceptions[0] is None
        assert exc.exceptions[1] is boom
        assert exc.exceptions[2] is None

    def test_reconcile_handles_all_failures(self) -> None:
        policy = BestEffortPolicy()
        e1 = ValueError("one")
        e2 = ValueError("two")

        with pytest.raises(PartialFailureError) as info:
            policy.reconcile([e1, e2])

        exc = info.value

        assert exc.failed_count == 2
        assert exc.successful_count == 0
        assert exc.results == [None, None]
