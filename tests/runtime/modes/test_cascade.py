"""Tests for Cascade mode."""

from __future__ import annotations

from typing import Any

from phronesis.runtime import Cascade, ExecutionContext, callable_node


async def _cheap(_c: ExecutionContext, _v: Any) -> str:
    return "cheap"


async def _expensive(_c: ExecutionContext, _v: Any) -> str:
    return "expensive"


class TestCascade:
    async def test_first_acceptable_wins(self, root_ctx: ExecutionContext) -> None:
        c = Cascade(
            nodes=(callable_node(_cheap), callable_node(_expensive)),
            acceptance=lambda o: o == "cheap",
        )
        outcome = await c(root_ctx, None)

        assert outcome.success
        assert outcome.output == "cheap"
        assert len(outcome.children) == 1

    async def test_falls_through_to_expensive(self, root_ctx: ExecutionContext) -> None:
        c = Cascade(
            nodes=(callable_node(_cheap), callable_node(_expensive)),
            acceptance=lambda o: o == "expensive",
        )
        outcome = await c(root_ctx, None)

        assert outcome.output == "expensive"
        assert len(outcome.children) == 2

    async def test_none_accepted_fails(self, root_ctx: ExecutionContext) -> None:
        c = Cascade(
            nodes=(callable_node(_cheap),),
            acceptance=lambda _o: False,
        )
        outcome = await c(root_ctx, None)

        assert not outcome.success
