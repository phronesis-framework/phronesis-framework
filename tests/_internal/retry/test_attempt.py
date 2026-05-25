"""Tests for AttemptInfo."""

from __future__ import annotations

from phronesis._internal.retry import AttemptInfo


class TestAttemptInfo:
    def test_carries_all_fields(self) -> None:
        exc = RuntimeError("x")
        a = AttemptInfo(
            attempt_number=2,
            exception=exc,
            duration_ms=12.0,
            delay_before_next_ms=500.0,
        )

        assert a.attempt_number == 2
        assert a.exception is exc
        assert a.duration_ms == 12.0
        assert a.delay_before_next_ms == 500.0

    def test_delay_can_be_none_for_final_attempt(self) -> None:
        a = AttemptInfo(
            attempt_number=3, exception=None, duration_ms=5.0, delay_before_next_ms=None
        )

        assert a.delay_before_next_ms is None
