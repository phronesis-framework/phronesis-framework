"""Tests for Loop mode."""

from __future__ import annotations

from typing import Any

from phronesis.runtime import ExecutionContext, Loop, LoopExhaustedError, callable_node


async def _inc(_ctx: ExecutionContext, value: Any) -> int:
    return int(value) + 1


class TestLoop:
    async def test_stops_when_predicate_false(self, root_ctx: ExecutionContext) -> None:
        loop = Loop(
            body=callable_node(_inc),
            until=lambda v: v < 3,
            max_iterations=10,
        )
        outcome = await loop(root_ctx, 0)

        assert outcome.success
        assert outcome.output == 3

    async def test_raises_when_max_iterations_reached(self, root_ctx: ExecutionContext) -> None:
        loop = Loop(
            body=callable_node(_inc),
            until=lambda _v: True,
            max_iterations=3,
        )
        outcome = await loop(root_ctx, 0)

        assert not outcome.success
        assert isinstance(outcome.error, LoopExhaustedError)

    async def test_body_failure_aborts(self, root_ctx: ExecutionContext) -> None:
        async def boom(_c: ExecutionContext, _v: Any) -> Any:
            raise RuntimeError("bad")

        loop = Loop(body=callable_node(boom), until=lambda _v: True, max_iterations=3)
        outcome = await loop(root_ctx, 0)

        assert not outcome.success
        assert isinstance(outcome.error, RuntimeError)
