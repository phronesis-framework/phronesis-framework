"""Integration tests combining multiple modes."""

from __future__ import annotations

from typing import Any

from phronesis.runtime import (
    ExecutionContext,
    Parallel,
    Retry,
    Sequence,
    callable_node,
)


class TestIntegration:
    async def test_sequence_with_parallel(self, root_ctx: ExecutionContext) -> None:
        async def upper(_c: ExecutionContext, value: Any) -> str:
            return str(value).upper()

        async def reverse(_c: ExecutionContext, value: Any) -> str:
            return str(value)[::-1]

        async def join(_c: ExecutionContext, value: Any) -> str:
            return "+".join(value)

        seq = Sequence(
            nodes=(
                Parallel(nodes=(callable_node(upper), callable_node(reverse))),
                callable_node(join),
            )
        )
        outcome = await seq(root_ctx, "hi")

        assert outcome.success
        assert outcome.output == "HI+ih"

    async def test_sequence_with_retry(self, root_ctx: ExecutionContext) -> None:
        calls = {"n": 0}

        async def flaky(_c: ExecutionContext, value: Any) -> int:
            calls["n"] += 1

            if calls["n"] < 2:
                raise RuntimeError("transient")

            return int(value) + 1

        async def double(_c: ExecutionContext, value: Any) -> int:
            return int(value) * 2

        seq = Sequence(
            nodes=(
                Retry(node=callable_node(flaky), max_attempts=5, backoff_initial_s=0.0),
                callable_node(double),
            )
        )
        outcome = await seq(root_ctx, 1)

        assert outcome.success
        assert outcome.output == 4
