"""Tests for the @with_retries decorator."""

from __future__ import annotations

import asyncio
from typing import Any

import pytest

from phronesis._internal.retry import (
    ExponentialBackoff,
    FixedBackoff,
    RetryExhaustedError,
    with_retries,
)


class _Transient(Exception):
    pass


class _Permanent(Exception):
    pass


class _WithRetryAfter(Exception):
    def __init__(self, message: str, retry_after_seconds: float) -> None:
        super().__init__(message)
        self.retry_after_seconds = retry_after_seconds


@pytest.fixture(autouse=True)
def _capture_sleeps(monkeypatch: pytest.MonkeyPatch) -> list[float]:
    """Replace ``asyncio.sleep`` with a no-op that records its argument."""
    delays: list[float] = []

    async def fake_sleep(delay: float) -> None:
        delays.append(delay)

    monkeypatch.setattr(asyncio, "sleep", fake_sleep)
    return delays


class TestHappyPath:
    async def test_returns_result_without_retry_when_no_exception(
        self, _capture_sleeps: list[float]
    ) -> None:
        calls = 0

        @with_retries(retry_on=(_Transient,))
        async def fn() -> int:
            nonlocal calls
            calls += 1
            return 42

        assert await fn() == 42
        assert calls == 1
        assert _capture_sleeps == []

    async def test_succeeds_after_some_failures(self, _capture_sleeps: list[float]) -> None:
        calls = 0

        @with_retries(retry_on=(_Transient,), backoff=FixedBackoff(0.0))
        async def fn() -> str:
            nonlocal calls
            calls += 1
            if calls < 3:
                raise _Transient("retry me")
            return "ok"

        assert await fn() == "ok"
        assert calls == 3
        assert len(_capture_sleeps) == 2


class TestRetryPolicy:
    async def test_does_not_retry_when_exception_not_in_retry_on(
        self, _capture_sleeps: list[float]
    ) -> None:
        @with_retries(retry_on=(_Transient,), backoff=FixedBackoff(0.0))
        async def fn() -> None:
            raise _Permanent("nope")

        with pytest.raises(_Permanent):
            await fn()
        assert _capture_sleeps == []

    async def test_should_retry_false_propagates(self, _capture_sleeps: list[float]) -> None:
        @with_retries(
            retry_on=(_Transient,),
            should_retry=lambda exc: False,
            backoff=FixedBackoff(0.0),
        )
        async def fn() -> None:
            raise _Transient("nope")

        with pytest.raises(_Transient):
            await fn()
        assert _capture_sleeps == []

    async def test_should_retry_true_allows_retry(self, _capture_sleeps: list[float]) -> None:
        calls = 0

        @with_retries(
            retry_on=(_Transient,),
            should_retry=lambda exc: True,
            backoff=FixedBackoff(0.0),
        )
        async def fn() -> int:
            nonlocal calls
            calls += 1
            if calls < 2:
                raise _Transient("retry")
            return 1

        assert await fn() == 1
        assert len(_capture_sleeps) == 1


class TestExhaustion:
    async def test_raises_retry_exhausted_with_history(self, _capture_sleeps: list[float]) -> None:
        @with_retries(retry_on=(_Transient,), max_attempts=3, backoff=FixedBackoff(0.0))
        async def fn() -> None:
            raise _Transient("always fails")

        with pytest.raises(RetryExhaustedError) as info:
            await fn()
        exc = info.value
        assert exc.attempts == 3
        assert isinstance(exc.last_exception, _Transient)
        assert len(exc.attempt_history) == 3
        # Last entry has no delay (no further retry scheduled).
        assert exc.attempt_history[-1].delay_before_next_ms is None
        # Earlier entries do have a delay.
        assert exc.attempt_history[0].delay_before_next_ms == 0.0

    async def test_max_attempts_one_raises_after_first_failure(
        self, _capture_sleeps: list[float]
    ) -> None:
        @with_retries(retry_on=(_Transient,), max_attempts=1, backoff=FixedBackoff(0.0))
        async def fn() -> None:
            raise _Transient("once")

        with pytest.raises(RetryExhaustedError):
            await fn()
        assert _capture_sleeps == []


class TestBackoffUsage:
    async def test_uses_exponential_backoff_by_default(self, _capture_sleeps: list[float]) -> None:
        @with_retries(
            retry_on=(_Transient,),
            max_attempts=4,
            backoff=ExponentialBackoff(initial=1.0, max_delay=100.0, jitter=False),
        )
        async def fn() -> None:
            raise _Transient("x")

        with pytest.raises(RetryExhaustedError):
            await fn()
        assert _capture_sleeps == [1.0, 2.0, 4.0]

    async def test_uses_fixed_backoff(self, _capture_sleeps: list[float]) -> None:
        @with_retries(retry_on=(_Transient,), max_attempts=3, backoff=FixedBackoff(0.25))
        async def fn() -> None:
            raise _Transient("x")

        with pytest.raises(RetryExhaustedError):
            await fn()
        assert _capture_sleeps == [0.25, 0.25]


class TestRetryAfter:
    async def test_honors_retry_after_when_enabled(self, _capture_sleeps: list[float]) -> None:
        @with_retries(
            retry_on=(_WithRetryAfter,),
            max_attempts=2,
            backoff=FixedBackoff(99.0),
            honor_retry_after=True,
        )
        async def fn() -> None:
            raise _WithRetryAfter("rate limited", retry_after_seconds=3.0)

        with pytest.raises(RetryExhaustedError):
            await fn()
        assert _capture_sleeps == [3.0]

    async def test_ignores_retry_after_when_disabled(self, _capture_sleeps: list[float]) -> None:
        @with_retries(
            retry_on=(_WithRetryAfter,),
            max_attempts=2,
            backoff=FixedBackoff(7.0),
            honor_retry_after=False,
        )
        async def fn() -> None:
            raise _WithRetryAfter("rate limited", retry_after_seconds=3.0)

        with pytest.raises(RetryExhaustedError):
            await fn()
        assert _capture_sleeps == [7.0]

    async def test_uses_backoff_when_attribute_missing(self, _capture_sleeps: list[float]) -> None:
        @with_retries(
            retry_on=(_Transient,),
            max_attempts=2,
            backoff=FixedBackoff(5.0),
            honor_retry_after=True,
        )
        async def fn() -> None:
            raise _Transient("no retry-after here")

        with pytest.raises(RetryExhaustedError):
            await fn()
        assert _capture_sleeps == [5.0]


class TestDelayHook:
    async def test_hook_value_is_used(self, _capture_sleeps: list[float]) -> None:
        @with_retries(
            retry_on=(_Transient,),
            max_attempts=2,
            backoff=FixedBackoff(99.0),
            delay_hook=lambda exc: 1.5,
        )
        async def fn() -> None:
            raise _Transient("x")

        with pytest.raises(RetryExhaustedError):
            await fn()
        assert _capture_sleeps == [1.5]

    async def test_hook_returns_none_falls_back_to_backoff(
        self, _capture_sleeps: list[float]
    ) -> None:
        @with_retries(
            retry_on=(_Transient,),
            max_attempts=2,
            backoff=FixedBackoff(2.0),
            delay_hook=lambda exc: None,
        )
        async def fn() -> None:
            raise _Transient("x")

        with pytest.raises(RetryExhaustedError):
            await fn()
        assert _capture_sleeps == [2.0]

    async def test_hook_takes_priority_over_retry_after(self, _capture_sleeps: list[float]) -> None:
        @with_retries(
            retry_on=(_WithRetryAfter,),
            max_attempts=2,
            backoff=FixedBackoff(99.0),
            honor_retry_after=True,
            delay_hook=lambda exc: 0.1,
        )
        async def fn() -> None:
            raise _WithRetryAfter("rl", retry_after_seconds=9.0)

        with pytest.raises(RetryExhaustedError):
            await fn()
        assert _capture_sleeps == [0.1]


class TestConcurrency:
    async def test_parallel_invocations_do_not_interfere(
        self, _capture_sleeps: list[float]
    ) -> None:
        counters: dict[str, int] = {}

        @with_retries(retry_on=(_Transient,), backoff=FixedBackoff(0.0))
        async def fn(key: str) -> int:
            counters[key] = counters.get(key, 0) + 1
            if counters[key] < 2:
                raise _Transient(key)
            return counters[key]

        results: list[Any] = await asyncio.gather(fn("a"), fn("b"), fn("c"))
        assert results == [2, 2, 2]
