"""Tests for gather_all."""

from __future__ import annotations

import asyncio

import pytest

from phronesis._internal.concurrency import (
    BestEffortPolicy,
    FailFastPolicy,
    PartialFailureError,
    gather_all,
)


async def _value(v: int, delay: float = 0.0) -> int:
    if delay:
        await asyncio.sleep(delay)

    return v


async def _fail(message: str, delay: float = 0.0) -> int:
    if delay:
        await asyncio.sleep(delay)

    raise RuntimeError(message)


class TestGatherAllDefault:
    async def test_default_policy_is_fail_fast(self) -> None:
        with pytest.raises(RuntimeError, match="boom"):
            await gather_all(_value(1), _fail("boom"), _value(3))

    async def test_returns_results_in_order(self) -> None:
        out = await gather_all(_value(1), _value(2), _value(3))

        assert out == [1, 2, 3]

    async def test_empty_input_returns_empty_list(self) -> None:
        out: list[int] = await gather_all()

        assert out == []


class TestGatherAllFailFast:
    async def test_propagates_first_exception(self) -> None:
        policy = FailFastPolicy()

        with pytest.raises(RuntimeError, match="x"):
            await gather_all(
                _value(1),
                _fail("x"),
                policy=policy,
            )

    async def test_returns_results_when_all_succeed(self) -> None:
        policy = FailFastPolicy()

        out = await gather_all(_value(10), _value(20), policy=policy)

        assert out == [10, 20]


class TestGatherAllBestEffort:
    async def test_collects_all_results_when_no_failures(self) -> None:
        policy = BestEffortPolicy()

        out = await gather_all(_value(1), _value(2), policy=policy)

        assert out == [1, 2]

    async def test_raises_partial_failure_when_any_failed(self) -> None:
        policy = BestEffortPolicy()

        with pytest.raises(PartialFailureError) as info:
            await gather_all(
                _value(1),
                _fail("oops"),
                _value(3),
                policy=policy,
            )

        exc = info.value

        assert exc.failed_count == 1
        assert exc.successful_count == 2
        assert exc.results[0] == 1
        assert exc.results[1] is None
        assert exc.results[2] == 3
        assert isinstance(exc.exceptions[1], RuntimeError)

    async def test_waits_for_all_tasks_even_when_one_fails_early(self) -> None:
        policy = BestEffortPolicy()
        completed: list[str] = []

        async def slow_ok() -> str:
            await asyncio.sleep(0.02)
            completed.append("slow")

            return "slow-ok"

        async def fast_fail() -> str:
            completed.append("fast")
            raise RuntimeError("fast-boom")

        with pytest.raises(PartialFailureError):
            await gather_all(slow_ok(), fast_fail(), policy=policy)

        assert "slow" in completed
        assert "fast" in completed
