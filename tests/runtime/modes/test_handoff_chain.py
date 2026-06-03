"""Tests for HandoffChain mode."""

from __future__ import annotations

from typing import Any

from phronesis.runtime import (
    ExecutionContext,
    HandoffChain,
    HandoffLimitError,
    callable_node,
)


class TestHandoffChain:
    async def test_terminates_when_no_handoff(self, root_ctx: ExecutionContext) -> None:
        async def a(_c: ExecutionContext, _v: Any) -> dict[str, Any]:
            return {"value": "done"}

        chain = HandoffChain(agents={"a": callable_node(a)}, initial="a")
        outcome = await chain(root_ctx, "start")

        assert outcome.success
        assert outcome.output == {"value": "done"}

    async def test_passes_turn(self, root_ctx: ExecutionContext) -> None:
        async def a(_c: ExecutionContext, _v: Any) -> dict[str, Any]:
            return {"handoff_to": "b", "value": "a-out"}

        async def b(_c: ExecutionContext, value: Any) -> dict[str, Any]:
            return {"final": value}

        chain = HandoffChain(
            agents={"a": callable_node(a), "b": callable_node(b)},
            initial="a",
        )
        outcome = await chain(root_ctx, "x")

        assert outcome.success
        assert outcome.output["final"]["value"] == "a-out"

    async def test_infinite_handoff_hits_limit(self, root_ctx: ExecutionContext) -> None:
        async def a(_c: ExecutionContext, _v: Any) -> dict[str, Any]:
            return {"handoff_to": "b"}

        async def b(_c: ExecutionContext, _v: Any) -> dict[str, Any]:
            return {"handoff_to": "a"}

        chain = HandoffChain(
            agents={"a": callable_node(a), "b": callable_node(b)},
            initial="a",
            max_handoffs=3,
        )
        outcome = await chain(root_ctx, None)

        assert not outcome.success
        assert isinstance(outcome.error, HandoffLimitError)
