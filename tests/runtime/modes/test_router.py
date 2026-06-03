"""Tests for Router mode."""

from __future__ import annotations

from typing import Any

from phronesis.runtime import ExecutionContext, NoMatchingRouteError, Router, callable_node


async def _a(_ctx: ExecutionContext, _v: Any) -> str:
    return "A"


async def _b(_ctx: ExecutionContext, _v: Any) -> str:
    return "B"


async def _default(_ctx: ExecutionContext, _v: Any) -> str:
    return "D"


class TestRouter:
    async def test_routes_to_known_key(self, root_ctx: ExecutionContext) -> None:
        r = Router(
            classifier=lambda v: v,
            routes={"a": callable_node(_a), "b": callable_node(_b)},
        )
        outcome = await r(root_ctx, "a")

        assert outcome.output == "A"

    async def test_falls_back_to_default(self, root_ctx: ExecutionContext) -> None:
        r = Router(
            classifier=lambda v: v,
            routes={"a": callable_node(_a)},
            default=callable_node(_default),
        )
        outcome = await r(root_ctx, "unknown")

        assert outcome.output == "D"

    async def test_no_route_without_default_fails(self, root_ctx: ExecutionContext) -> None:
        r = Router(
            classifier=lambda v: v,
            routes={"a": callable_node(_a)},
        )
        outcome = await r(root_ctx, "unknown")

        assert not outcome.success
        assert isinstance(outcome.error, NoMatchingRouteError)

    async def test_async_classifier(self, root_ctx: ExecutionContext) -> None:
        async def cls(_v: Any) -> str:
            return "b"

        r = Router(
            classifier=cls,
            routes={"a": callable_node(_a), "b": callable_node(_b)},
        )
        outcome = await r(root_ctx, None)

        assert outcome.output == "B"
