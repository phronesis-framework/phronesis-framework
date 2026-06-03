"""Tests for :meth:`Pipeline.run` convenience entry point."""

from __future__ import annotations

from typing import Any

from phronesis.pipelines import pipeline
from phronesis.runtime import ExecutionContext


async def _inc(_ctx: ExecutionContext, value: Any) -> Any:
    return value + 1


async def _stash_metadata(ctx: ExecutionContext, value: Any) -> Any:
    return {"value": value, "tag": ctx.metadata.get("tag"), "deadline": ctx.deadline}


class TestRun:
    async def test_run_executes_with_fresh_root_context(self) -> None:
        p = pipeline(_inc, _inc, name="run-basic")

        outcome = await p.run(0)

        assert outcome.success
        assert outcome.output == 2

    async def test_run_applies_metadata(self) -> None:
        p = pipeline(_stash_metadata, name="meta")

        outcome = await p.run("x", metadata={"tag": "alpha"})

        assert outcome.success
        assert outcome.output["tag"] == "alpha"
        assert outcome.output["value"] == "x"

    async def test_run_applies_deadline(self) -> None:
        p = pipeline(_stash_metadata, name="deadline")

        outcome = await p.run("x", deadline_s=0.5)

        assert outcome.success
        assert outcome.output["deadline"] is not None
