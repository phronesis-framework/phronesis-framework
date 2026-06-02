"""Tests for Fallback mode."""

from __future__ import annotations

from typing import Any

from phronesis.runtime import ExecutionContext, Fallback, callable_node


async def _fail(_c: ExecutionContext, _v: Any) -> None:
    raise RuntimeError("bad")


async def _ok(_c: ExecutionContext, _v: Any) -> str:
    return "ok"


class TestFallback:
    async def test_primary_succeeds(self, root_ctx: ExecutionContext) -> None:
        fb = Fallback(primary=callable_node(_ok), fallbacks=(callable_node(_fail),))
        outcome = await fb(root_ctx, None)

        assert outcome.success
        assert outcome.output == "ok"
        assert len(outcome.children) == 1

    async def test_falls_back(self, root_ctx: ExecutionContext) -> None:
        fb = Fallback(primary=callable_node(_fail), fallbacks=(callable_node(_ok),))
        outcome = await fb(root_ctx, None)

        assert outcome.success
        assert outcome.output == "ok"
        assert len(outcome.children) == 2

    async def test_all_fail(self, root_ctx: ExecutionContext) -> None:
        fb = Fallback(primary=callable_node(_fail), fallbacks=(callable_node(_fail),))
        outcome = await fb(root_ctx, None)

        assert not outcome.success
