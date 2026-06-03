"""Tests for Race mode."""

from __future__ import annotations

import asyncio
from typing import Any

from phronesis.runtime import ExecutionContext, Race, callable_node


async def _fast(_ctx: ExecutionContext, _value: Any) -> str:
    return "fast"


async def _slow(_ctx: ExecutionContext, _value: Any) -> str:
    await asyncio.sleep(0.05)
    return "slow"


async def _fail_fast(_ctx: ExecutionContext, _value: Any) -> str:
    raise RuntimeError("fail")


class TestRace:
    async def test_returns_first_winner(self, root_ctx: ExecutionContext) -> None:
        race = Race(nodes=(callable_node(_slow), callable_node(_fast)))
        outcome = await race(root_ctx, None)

        assert outcome.success
        assert outcome.output == "fast"

    async def test_failing_node_does_not_block_others(self, root_ctx: ExecutionContext) -> None:
        race = Race(nodes=(callable_node(_fail_fast), callable_node(_slow)))
        outcome = await race(root_ctx, None)

        assert outcome.success
        assert outcome.output == "slow"

    async def test_all_fail(self, root_ctx: ExecutionContext) -> None:
        race = Race(nodes=(callable_node(_fail_fast), callable_node(_fail_fast)))
        outcome = await race(root_ctx, None)

        assert not outcome.success

    async def test_empty_race_fails(self, root_ctx: ExecutionContext) -> None:
        race = Race(nodes=())
        outcome = await race(root_ctx, None)

        assert not outcome.success
