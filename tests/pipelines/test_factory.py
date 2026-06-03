"""Tests for the :func:`pipeline` factory and step adaptation."""

from __future__ import annotations

from typing import Any

import pytest

from phronesis.pipelines import Pipeline, pipeline
from phronesis.pipelines.ids import _new_pipeline_id
from phronesis.runtime import ExecutionContext, callable_node


async def _inc(_ctx: ExecutionContext, value: Any) -> Any:
    return value + 1


async def _double_only_value(value: Any) -> Any:
    return value * 2


class TestFactory:
    def test_returns_pipeline_instance(self) -> None:
        p = pipeline(callable_node(_inc), name="returns")

        assert isinstance(p, Pipeline)
        assert p.name == "returns"

    def test_assigns_default_pipeline_id_from_name(self) -> None:
        p = pipeline(callable_node(_inc), name="defaulted")

        assert p.pipeline_id.canonical == "phronesis.pipelines.pipeline.defaulted"

    def test_normalises_name_with_invalid_characters(self) -> None:
        p = pipeline(callable_node(_inc), name="My Pipeline-1")

        assert p.pipeline_id.canonical == "phronesis.pipelines.pipeline.my_pipeline_1"

    def test_uses_explicit_pipeline_id_when_provided(self) -> None:
        explicit = _new_pipeline_id("explicit-id")

        p = pipeline(callable_node(_inc), name="anything", pipeline_id=explicit)

        assert p.pipeline_id is explicit


class TestStepAdaptation:
    async def test_adapts_bare_async_callable(self, root_ctx: ExecutionContext) -> None:
        p = pipeline(_double_only_value, name="bare-callable")

        outcome = await p(root_ctx, 3)

        assert outcome.success
        assert outcome.output == 6

    async def test_adapts_ctx_aware_callable(self, root_ctx: ExecutionContext) -> None:
        p = pipeline(_inc, name="ctx-aware")

        outcome = await p(root_ctx, 41)

        assert outcome.success
        assert outcome.output == 42

    async def test_passes_through_existing_executable(self, root_ctx: ExecutionContext) -> None:
        node = callable_node(_inc)

        p = pipeline(node, name="passthrough")

        assert p.steps[0] is node

    def test_rejects_unsupported_step_type(self) -> None:
        with pytest.raises(TypeError):
            pipeline(123, name="bad")  # type: ignore[arg-type]

    def test_empty_factory_builds_pipeline_without_steps(self) -> None:
        p = pipeline(name="empty")

        assert p.steps == ()
