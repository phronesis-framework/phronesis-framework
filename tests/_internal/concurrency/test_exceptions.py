"""Tests for concurrency exceptions."""

from __future__ import annotations

from phronesis._internal.concurrency import ConcurrencyError, PartialFailureError


class TestPartialFailureError:
    def test_is_concurrency_error(self) -> None:
        exc = PartialFailureError("x", results=[], exceptions=[])

        assert isinstance(exc, ConcurrencyError)

    def test_counts_failures_and_successes(self) -> None:
        boom = RuntimeError("boom")
        exc = PartialFailureError(
            "1 of 3 tasks failed",
            results=[1, None, 3],
            exceptions=[None, boom, None],
        )

        assert exc.failed_count == 1
        assert exc.successful_count == 2

    def test_preserves_ordered_results_and_exceptions(self) -> None:
        boom = ValueError("boom")
        exc = PartialFailureError(
            "1 of 2 tasks failed",
            results=[None, "ok"],
            exceptions=[boom, None],
        )

        assert exc.results == [None, "ok"]
        assert exc.exceptions[0] is boom
        assert exc.exceptions[1] is None

    def test_message_preserved(self) -> None:
        exc = PartialFailureError("custom message", results=[], exceptions=[])

        assert str(exc) == "custom message"
