"""Tests for TreeSearch mode."""

from __future__ import annotations

from typing import Any

from phronesis.runtime import ExecutionContext, TreeSearch, callable_node


class TestTreeSearch:
    async def test_returns_best_candidate(self, root_ctx: ExecutionContext) -> None:
        async def expander(_c: ExecutionContext, node: Any) -> list[int]:
            return [node + 1, node + 2, node + 3]

        async def evaluator(_c: ExecutionContext, node: Any) -> float:
            return float(node)

        ts = TreeSearch(
            expander=callable_node(expander),
            evaluator=callable_node(evaluator),
            max_depth=2,
            beam_width=2,
        )
        outcome = await ts(root_ctx, 0)

        assert outcome.success
        assert outcome.output >= 3

    async def test_empty_expansion_returns_failure(self, root_ctx: ExecutionContext) -> None:
        async def expander(_c: ExecutionContext, _node: Any) -> list[int]:
            return []

        async def evaluator(_c: ExecutionContext, _node: Any) -> float:
            return 1.0

        ts = TreeSearch(
            expander=callable_node(expander),
            evaluator=callable_node(evaluator),
            max_depth=2,
        )
        outcome = await ts(root_ctx, 0)

        assert not outcome.success
