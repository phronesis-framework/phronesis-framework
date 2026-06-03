"""Tests for Retry mode."""

from __future__ import annotations

from typing import Any

from phronesis.runtime import ExecutionContext, Retry, callable_node


class TestRetry:
    async def test_succeeds_on_first_try(self, root_ctx: ExecutionContext) -> None:
        async def ok(_c: ExecutionContext, _v: Any) -> str:
            return "ok"

        r = Retry(node=callable_node(ok), max_attempts=3, backoff_initial_s=0.0)
        outcome = await r(root_ctx, None)

        assert outcome.success
        assert outcome.output == "ok"

    async def test_retries_until_success(self, root_ctx: ExecutionContext) -> None:
        calls = {"n": 0}

        async def flaky(_c: ExecutionContext, _v: Any) -> str:
            calls["n"] += 1

            if calls["n"] < 3:
                raise RuntimeError("transient")

            return "won"

        r = Retry(node=callable_node(flaky), max_attempts=5, backoff_initial_s=0.0)
        outcome = await r(root_ctx, None)

        assert outcome.success
        assert outcome.output == "won"
        assert calls["n"] == 3

    async def test_gives_up_after_max_attempts(self, root_ctx: ExecutionContext) -> None:
        async def fail(_c: ExecutionContext, _v: Any) -> None:
            raise ValueError("nope")

        r = Retry(node=callable_node(fail), max_attempts=2, backoff_initial_s=0.0)
        outcome = await r(root_ctx, None)

        assert not outcome.success
        assert isinstance(outcome.error, ValueError)

    async def test_non_matching_exception_not_retried(self, root_ctx: ExecutionContext) -> None:
        calls = {"n": 0}

        async def fail(_c: ExecutionContext, _v: Any) -> None:
            calls["n"] += 1
            raise KeyError("not retryable")

        r = Retry(
            node=callable_node(fail),
            max_attempts=3,
            backoff_initial_s=0.0,
            on=(ValueError,),
        )
        outcome = await r(root_ctx, None)

        assert not outcome.success
        assert calls["n"] == 1
