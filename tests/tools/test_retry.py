"""Tests for :class:`RetryPolicy`."""

from __future__ import annotations

import pytest

from phronesis.tools.errors import ToolError, ToolValidationError
from phronesis.tools.retry import NO_RETRY, RetryPolicy


class _BoomError(ToolError):
    pass


class TestRetryPolicy:
    def test_default_max_attempts_is_one(self) -> None:
        policy = RetryPolicy()

        assert policy.max_attempts == 1

    def test_below_one_is_clamped(self) -> None:
        policy = RetryPolicy(max_attempts=0)

        assert policy.max_attempts == 1

    def test_should_retry_default_includes_tool_errors(self) -> None:
        policy = RetryPolicy(max_attempts=3)

        assert policy.should_retry(_BoomError("x", details={})) is True

    def test_should_retry_excludes_validation_errors(self) -> None:
        policy = RetryPolicy(max_attempts=3)

        assert policy.should_retry(ToolValidationError("x", details={})) is False

    def test_should_retry_custom_retry_on(self) -> None:
        policy = RetryPolicy(max_attempts=2, retry_on=(ValueError,))

        assert policy.should_retry(ValueError("x")) is True
        assert policy.should_retry(_BoomError("x", details={})) is False

    def test_no_retry_singleton(self) -> None:
        assert NO_RETRY.max_attempts == 1


class TestRetryPolicyIsFrozen:
    def test_cannot_mutate(self) -> None:
        policy = RetryPolicy(max_attempts=3)

        with pytest.raises(AttributeError):
            policy.max_attempts = 99  # type: ignore[misc]
