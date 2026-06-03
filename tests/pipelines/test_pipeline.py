"""Tests for the :class:`Pipeline` core semantics."""

from __future__ import annotations

from collections.abc import Callable
from typing import Any

from phronesis.pipelines import Pipeline, PipelineEmptyError, pipeline
from phronesis.runtime import ExecutionContext, callable_node
from phronesis.runtime.errors import CancelledError
from phronesis.runtime.protocol import Executable


async def _inc(_ctx: ExecutionContext, value: Any) -> Any:
    return value + 1


async def _double(_ctx: ExecutionContext, value: Any) -> Any:
    return value * 2


async def _stringify(_ctx: ExecutionContext, value: Any) -> Any:
    return f"v={value}"


class TestPipelineHappyPath:
    async def test_chains_outputs_across_steps(self, root_ctx: ExecutionContext) -> None:
        p = pipeline(callable_node(_inc), callable_node(_double), name="happy")

        outcome = await p(root_ctx, 1)

        assert outcome.success
        assert outcome.output == 4
        assert len(outcome.children) == 2

    async def test_threads_arbitrary_types_between_steps(self, root_ctx: ExecutionContext) -> None:
        p = pipeline(callable_node(_inc), callable_node(_stringify), name="types")

        outcome = await p(root_ctx, 41)

        assert outcome.success
        assert outcome.output == "v=42"


class TestPipelineEmpty:
    async def test_empty_pipeline_fails_with_typed_error(self, root_ctx: ExecutionContext) -> None:
        p = pipeline(name="nada")

        outcome = await p(root_ctx, "anything")

        assert not outcome.success
        assert isinstance(outcome.error, PipelineEmptyError)
        assert outcome.children == ()


class TestPipelineFailure:
    async def test_first_failure_short_circuits(
        self,
        root_ctx: ExecutionContext,
        make_failing_node: Callable[[Exception], Executable],
    ) -> None:
        boom = RuntimeError("boom")
        p = pipeline(
            callable_node(_inc),
            make_failing_node(boom),
            callable_node(_double),
            name="abort",
        )

        outcome = await p(root_ctx, 1)

        assert not outcome.success
        assert outcome.error is boom
        assert len(outcome.children) == 2


class TestPipelineCancellation:
    async def test_cancellation_before_first_step_aborts(self, root_ctx: ExecutionContext) -> None:
        root_ctx.cancel()
        p = pipeline(callable_node(_inc), name="cancelled")

        outcome = await p(root_ctx, 1)

        assert not outcome.success
        assert isinstance(outcome.error, CancelledError)

    async def test_cancellation_between_steps_stops_iteration(
        self,
        root_ctx: ExecutionContext,
    ) -> None:
        executed: list[str] = []

        async def step_one(_ctx: ExecutionContext, value: Any) -> Any:
            executed.append("one")
            root_ctx.cancel()
            return value + 1

        async def step_two(_ctx: ExecutionContext, value: Any) -> Any:  # pragma: no cover
            executed.append("two")
            return value * 2

        p = pipeline(callable_node(step_one), callable_node(step_two), name="mid-cancel")

        outcome = await p(root_ctx, 1)

        assert not outcome.success
        assert isinstance(outcome.error, CancelledError)
        assert executed == ["one"]


class TestPipelineObservability:
    async def test_span_extra_includes_pipeline_attrs(
        self,
        root_ctx: ExecutionContext,
        monkeypatch: Any,
    ) -> None:
        import sys
        from contextlib import asynccontextmanager

        from phronesis.obs.attributes import PIPELINE_ID, PIPELINE_NAME

        captured: dict[str, Any] = {}

        @asynccontextmanager
        async def fake_span(
            mode: str,
            *,
            run_id: str | None = None,
            parent_id: str | None = None,
            extra: Any = None,
        ) -> Any:
            captured["mode"] = mode
            captured["extra"] = dict(extra) if extra is not None else {}
            yield None

        module = sys.modules["phronesis.pipelines.pipeline"]
        monkeypatch.setattr(module, "runtime_span", fake_span)

        p = pipeline(callable_node(_inc), name="obs")
        outcome = await p(root_ctx, 0)

        assert outcome.success
        assert captured["mode"] == "pipeline"
        assert captured["extra"][PIPELINE_NAME] == "obs"
        assert captured["extra"][PIPELINE_ID].startswith("phronesis.pipelines.pipeline.")


class TestPipelineDataclass:
    def test_pipeline_is_frozen(self) -> None:
        p = pipeline(callable_node(_inc), name="frozen")

        try:
            p.name = "other"  # type: ignore[misc]
        except Exception as exc:
            assert isinstance(exc, (AttributeError, TypeError))
        else:  # pragma: no cover - safety net
            raise AssertionError("Pipeline must be frozen")

    def test_steps_are_tuple_of_executables(self) -> None:
        p = pipeline(callable_node(_inc), callable_node(_double), name="shape")

        assert isinstance(p, Pipeline)
        assert isinstance(p.steps, tuple)
        assert len(p.steps) == 2
