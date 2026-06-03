"""Tests for runtime observability primitives."""

from __future__ import annotations

from phronesis.runtime import ExecutionContext
from phronesis.runtime.obs import (
    RUNTIME_CHILDREN_COUNT,
    RUNTIME_HANDOFF_FROM,
    RUNTIME_HANDOFF_TO,
    RUNTIME_ITERATION,
    RUNTIME_MODE,
    RUNTIME_ROUTE,
    RUNTIME_RUN_ID,
    runtime_span,
)


class TestObsConstants:
    def test_attribute_names_are_dot_separated(self) -> None:
        for name in (
            RUNTIME_MODE,
            RUNTIME_RUN_ID,
            RUNTIME_CHILDREN_COUNT,
            RUNTIME_ITERATION,
            RUNTIME_ROUTE,
            RUNTIME_HANDOFF_FROM,
            RUNTIME_HANDOFF_TO,
        ):
            assert name.startswith("runtime.")

    def test_attribute_names_are_unique(self) -> None:
        names = {
            RUNTIME_MODE,
            RUNTIME_RUN_ID,
            RUNTIME_CHILDREN_COUNT,
            RUNTIME_ITERATION,
            RUNTIME_ROUTE,
            RUNTIME_HANDOFF_FROM,
            RUNTIME_HANDOFF_TO,
        }
        assert len(names) == 7


class TestRuntimeSpan:
    async def test_runtime_span_is_noop_when_obs_not_configured(self) -> None:
        ctx = ExecutionContext.new()

        async with runtime_span("sequence", run_id=ctx.run_id.canonical) as span:
            assert span is not None
