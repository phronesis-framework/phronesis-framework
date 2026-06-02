"""Tests for MapReduce mode."""

from __future__ import annotations

from typing import Any

from phronesis.runtime import ExecutionContext, MapReduce, callable_node


async def _double(_ctx: ExecutionContext, value: Any) -> int:
    return int(value) * 2


async def _fail(_ctx: ExecutionContext, _value: Any) -> int:
    raise ValueError("bad")


class TestMapReduce:
    async def test_splits_maps_reduces(self, root_ctx: ExecutionContext) -> None:
        mr = MapReduce(
            splitter=lambda v: list(v),
            mapper=callable_node(_double),
            reducer=lambda outs: sum(outs),
        )
        outcome = await mr(root_ctx, [1, 2, 3])

        assert outcome.success
        assert outcome.output == 12

    async def test_async_reducer(self, root_ctx: ExecutionContext) -> None:
        async def reducer(outs: Any) -> list[Any]:
            return list(outs)

        mr = MapReduce(
            splitter=lambda v: list(v),
            mapper=callable_node(_double),
            reducer=reducer,
        )
        outcome = await mr(root_ctx, [1, 2])

        assert outcome.output == [2, 4]

    async def test_mapper_failure_propagates(self, root_ctx: ExecutionContext) -> None:
        mr = MapReduce(
            splitter=lambda v: list(v),
            mapper=callable_node(_fail),
            reducer=lambda outs: outs,
        )
        outcome = await mr(root_ctx, [1, 2])

        assert not outcome.success
