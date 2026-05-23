"""Tests for backoff strategies."""

from __future__ import annotations

from phronesis._internal.retry import (
    BackoffStrategy,
    ExponentialBackoff,
    FixedBackoff,
)


class TestFixedBackoff:
    def test_returns_constant_delay(self) -> None:
        b = FixedBackoff(delay=2.5)

        assert b.get_delay(1) == 2.5
        assert b.get_delay(5) == 2.5

    def test_satisfies_backoff_strategy_protocol(self) -> None:
        assert isinstance(FixedBackoff(1.0), BackoffStrategy)


class TestExponentialBackoff:
    def test_without_jitter_doubles_each_attempt(self) -> None:
        b = ExponentialBackoff(initial=1.0, max_delay=100.0, jitter=False)

        assert b.get_delay(1) == 1.0
        assert b.get_delay(2) == 2.0
        assert b.get_delay(3) == 4.0
        assert b.get_delay(4) == 8.0

    def test_respects_max_delay(self) -> None:
        b = ExponentialBackoff(initial=1.0, max_delay=5.0, jitter=False)

        assert b.get_delay(10) == 5.0

    def test_jitter_keeps_delay_in_50_to_150_percent_range(self) -> None:
        b = ExponentialBackoff(initial=2.0, max_delay=100.0, jitter=True)
        base = 2.0  # attempt 1

        for _ in range(100):
            d = b.get_delay(1)

            assert base * 0.5 <= d < base * 1.5

    def test_satisfies_backoff_strategy_protocol(self) -> None:
        assert isinstance(ExponentialBackoff(), BackoffStrategy)
