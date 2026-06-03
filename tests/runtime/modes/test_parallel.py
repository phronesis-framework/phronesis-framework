"""Tests for Parallel mode."""

from __future__ import annotations

import asyncio
from typing import Any

from phronesis._internal.concurrency import BestEffortPolicy
from phronesis.runtime import ExecutionContext, Parallel, callable_node


async def _slow(_ctx: ExecutionContext, value: Any) -> Any:
    await asyncio.sleep(0.01)
    return value


async def _double(_ctx: ExecutionContext, value: Any) -> Any:
    return value * 2


async def _fail(_ctx: ExecutionContext, _value: Any) -> Any:
    raise ValueError("bad")


class TestParallel:
    async def test_returns_tuple_of_outputs(self, root_ctx: ExecutionContext) -> None:
        par = Parallel(nodes=(callable_node(_slow), callable_node(_double)))
        outcome = await par(root_ctx, 3)

        assert outcome.success
        assert outcome.output == (3, 6)

    async def test_fail_fast_propagates(self, root_ctx: ExecutionContext) -> None:
        par = Parallel(nodes=(callable_node(_fail), callable_node(_double)))
        outcome = await par(root_ctx, 3)

        assert not outcome.success
        assert outcome.error is not None

    async def test_best_effort_collects_failures(self, root_ctx: ExecutionContext) -> None:
        par = Parallel(
            nodes=(callable_node(_fail), callable_node(_double)),
            policy=BestEffortPolicy(),
        )
        outcome = await par(root_ctx, 5)

        assert not outcome.success
        assert len(outcome.children) == 2

    async def test_empty_parallel_succeeds(self, root_ctx: ExecutionContext) -> None:
        par = Parallel(nodes=())
        outcome = await par(root_ctx, "x")

        assert outcome.success
        assert outcome.output == ()
