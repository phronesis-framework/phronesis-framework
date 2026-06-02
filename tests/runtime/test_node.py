"""Tests for node adapters: callable_node, agent_node, as_node."""

from __future__ import annotations

from typing import Any

import pytest

from phronesis.runtime import (
    ExecutionContext,
    RunOutcome,
    as_node,
    callable_node,
)


class TestCallableNode:
    async def test_two_arg_callable(self, root_ctx: ExecutionContext) -> None:
        async def fn(ctx: ExecutionContext, value: Any) -> str:
            assert ctx is root_ctx
            return f"got:{value}"

        node = callable_node(fn)
        outcome = await node(root_ctx, "hi")

        assert outcome.success
        assert outcome.output == "got:hi"

    async def test_one_arg_callable(self, root_ctx: ExecutionContext) -> None:
        async def fn(value: Any) -> str:
            return str(value).upper()

        node = callable_node(fn)
        outcome = await node(root_ctx, "hi")

        assert outcome.output == "HI"

    async def test_callable_raising_yields_fail_outcome(self, root_ctx: ExecutionContext) -> None:
        async def fn(_v: Any) -> None:
            raise ValueError("boom")

        node = callable_node(fn)
        outcome = await node(root_ctx, None)

        assert not outcome.success
        assert isinstance(outcome.error, ValueError)

    async def test_callable_returning_outcome_passes_through(
        self, root_ctx: ExecutionContext
    ) -> None:
        original = RunOutcome.ok(output="explicit")

        async def fn(_v: Any) -> RunOutcome:
            return original

        node = callable_node(fn)
        outcome = await node(root_ctx, None)

        assert outcome is original


class TestAsNode:
    async def test_async_function_becomes_callable_node(self, root_ctx: ExecutionContext) -> None:
        async def fn(value: Any) -> str:
            return str(value)

        node = as_node(fn)
        outcome = await node(root_ctx, 7)

        assert outcome.output == "7"

    def test_unsupported_raises(self) -> None:
        with pytest.raises(TypeError):
            as_node(123)
