"""Tests for Debate mode."""

from __future__ import annotations

from typing import Any

from phronesis.runtime import Debate, ExecutionContext, callable_node


class TestDebate:
    async def test_collects_transcript(self, root_ctx: ExecutionContext) -> None:
        async def p1(_c: ExecutionContext, payload: Any) -> str:
            return f"p1:r{payload['round']}"

        async def p2(_c: ExecutionContext, payload: Any) -> str:
            return f"p2:r{payload['round']}"

        d = Debate(participants=(callable_node(p1), callable_node(p2)), rounds=2)
        outcome = await d(root_ctx, "topic")

        assert outcome.success
        assert len(outcome.output) == 4

    async def test_moderator_synthesises(self, root_ctx: ExecutionContext) -> None:
        async def p(_c: ExecutionContext, payload: Any) -> str:
            return f"r{payload['round']}"

        async def mod(_c: ExecutionContext, payload: Any) -> str:
            return f"final({len(payload['transcript'])})"

        d = Debate(
            participants=(callable_node(p),),
            rounds=2,
            moderator=callable_node(mod),
        )
        outcome = await d(root_ctx, "topic")

        assert outcome.output == "final(2)"
