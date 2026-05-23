"""Tests for retry exceptions."""

from __future__ import annotations

import pytest

from phronesis._internal.retry import (
    AttemptInfo,
    RetryError,
    RetryExhaustedError,
)


class TestRetryExhaustedError:
    def test_is_retry_error(self) -> None:
        assert issubclass(RetryExhaustedError, RetryError)

    def test_carries_history_and_last_exception(self) -> None:
        last = RuntimeError("boom")
        history = [
            AttemptInfo(1, RuntimeError("a"), 1.0, 100.0),
            AttemptInfo(2, last, 1.0, None),
        ]

        with pytest.raises(RetryExhaustedError) as info:
            raise RetryExhaustedError(
                attempts=2,
                total_duration_ms=10.0,
                last_exception=last,
                attempt_history=history,
            )

        exc = info.value

        assert exc.attempts == 2
        assert exc.total_duration_ms == 10.0
        assert exc.last_exception is last
        assert exc.attempt_history is history
