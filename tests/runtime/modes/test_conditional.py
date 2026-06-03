"""Tests for Conditional mode."""

from __future__ import annotations

from typing import Any

from phronesis.runtime import Conditional, ExecutionContext, callable_node


async def _yes(_ctx: ExecutionContext, _value: Any) -> str:
    return "yes"


async def _no(_ctx: ExecutionContext, _value: Any) -> str:
    return "no"


class TestConditional:
    async def test_takes_truthy_branch(self, root_ctx: ExecutionContext) -> None:
        cond = Conditional(
            predicate=lambda v: v > 0,
            on_true=callable_node(_yes),
            on_false=callable_node(_no),
        )
        outcome = await cond(root_ctx, 5)

        assert outcome.output == "yes"

    async def test_takes_falsy_branch(self, root_ctx: ExecutionContext) -> None:
        cond = Conditional(
            predicate=lambda v: v > 0,
            on_true=callable_node(_yes),
            on_false=callable_node(_no),
        )
        outcome = await cond(root_ctx, -1)

        assert outcome.output == "no"

    async def test_async_predicate(self, root_ctx: ExecutionContext) -> None:
        async def pred(v: Any) -> bool:
            return bool(v == "go")

        cond = Conditional(
            predicate=pred,
            on_true=callable_node(_yes),
            on_false=callable_node(_no),
        )
        outcome = await cond(root_ctx, "go")

        assert outcome.output == "yes"
