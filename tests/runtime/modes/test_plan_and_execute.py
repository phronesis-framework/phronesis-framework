"""Tests for PlanAndExecute mode."""

from __future__ import annotations

from typing import Any

from phronesis.runtime import ExecutionContext, PlanAndExecute, callable_node


class TestPlanAndExecute:
    async def test_runs_each_step(self, root_ctx: ExecutionContext) -> None:
        async def planner(_c: ExecutionContext, _v: Any) -> dict[str, Any]:
            return {"steps": ["a", "b", "c"]}

        async def executor(_c: ExecutionContext, step: Any) -> str:
            return f"did-{step}"

        p = PlanAndExecute(
            planner=callable_node(planner),
            executor=callable_node(executor),
        )
        outcome = await p(root_ctx, None)

        assert outcome.success
        assert outcome.output == ("did-a", "did-b", "did-c")

    async def test_step_failure_aborts(self, root_ctx: ExecutionContext) -> None:
        async def planner(_c: ExecutionContext, _v: Any) -> dict[str, Any]:
            return {"steps": ["a", "b"]}

        async def executor(_c: ExecutionContext, step: Any) -> str:
            if step == "b":
                raise RuntimeError("bad")

            return str(step)

        p = PlanAndExecute(
            planner=callable_node(planner),
            executor=callable_node(executor),
        )
        outcome = await p(root_ctx, None)

        assert not outcome.success

    async def test_planner_failure_aborts(self, root_ctx: ExecutionContext) -> None:
        async def planner(_c: ExecutionContext, _v: Any) -> dict[str, Any]:
            raise RuntimeError("plan failed")

        async def executor(_c: ExecutionContext, step: Any) -> str:
            return str(step)

        p = PlanAndExecute(
            planner=callable_node(planner),
            executor=callable_node(executor),
        )
        outcome = await p(root_ctx, None)

        assert not outcome.success
