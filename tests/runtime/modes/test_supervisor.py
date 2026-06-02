"""Tests for Supervisor mode."""

from __future__ import annotations

from typing import Any

from phronesis.runtime import ExecutionContext, LoopExhaustedError, Supervisor, callable_node


class TestSupervisor:
    async def test_terminates_when_supervisor_emits_none_route(
        self, root_ctx: ExecutionContext
    ) -> None:
        async def sup(_c: ExecutionContext, value: Any) -> dict[str, Any]:
            return {"final": value}

        s = Supervisor(supervisor=callable_node(sup), workers={}, max_iterations=3)
        outcome = await s(root_ctx, "x")

        assert outcome.success
        assert outcome.output == {"final": "x"}

    async def test_routes_to_worker(self, root_ctx: ExecutionContext) -> None:
        seq = iter([{"route": "a"}, {"final": "done"}])

        async def sup(_c: ExecutionContext, _v: Any) -> dict[str, Any]:
            return next(seq)

        async def worker_a(_c: ExecutionContext, value: Any) -> str:
            return "after_a"

        s = Supervisor(
            supervisor=callable_node(sup),
            workers={"a": callable_node(worker_a)},
            max_iterations=3,
        )
        outcome = await s(root_ctx, "start")

        assert outcome.success
        assert outcome.output == {"final": "done"}

    async def test_max_iterations_exhausted(self, root_ctx: ExecutionContext) -> None:
        async def sup(_c: ExecutionContext, _v: Any) -> dict[str, Any]:
            return {"route": "a"}

        async def worker_a(_c: ExecutionContext, _v: Any) -> dict[str, Any]:
            return {}

        s = Supervisor(
            supervisor=callable_node(sup),
            workers={"a": callable_node(worker_a)},
            max_iterations=2,
        )
        outcome = await s(root_ctx, "x")

        assert not outcome.success
        assert isinstance(outcome.error, LoopExhaustedError)
