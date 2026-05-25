"""Tests for single-model tool detection, validation and schema (D-12)."""

from __future__ import annotations

import asyncio
from typing import Annotated

import pytest
from pydantic import BaseModel, Field

from phronesis.context.context import Context
from phronesis.tools.errors import ToolValidationError
from phronesis.tools.schema import build_canonical_schema
from phronesis.tools.single_model import get_single_model
from phronesis.tools.spec import ToolSpec
from phronesis.tools.tool import Tool
from phronesis.tools.tool_id import ToolId, ToolName
from phronesis.tools.validation import build_validator


def _spec() -> ToolSpec:
    return ToolSpec(
        id=ToolId("phronesis.tools.run"),
        name=ToolName("run"),
        description="Runs a job.",
    )


class JobInput(BaseModel):
    name: str
    count: int = Field(ge=1)


def _single_model_tool(payload: JobInput) -> str:
    return f"{payload.name}x{payload.count}"


async def _single_model_async(payload: JobInput) -> str:
    return f"{payload.name}-{payload.count}"


def _single_model_with_context(payload: JobInput, ctx: Context) -> str:
    trace = ctx.trace_id or "?"
    return f"{payload.name} [{trace}]"


def _annotated_model_param(payload: Annotated[JobInput, "the input"]) -> str:
    return payload.name


def _two_model_params(a: JobInput, b: JobInput) -> None: ...


def _mixed_params(payload: JobInput, extra: int) -> None: ...


def _no_models(x: int) -> int:
    return x


class TestGetSingleModel:
    def test_returns_param_and_model(self) -> None:
        result = get_single_model(_single_model_tool)

        assert result == ("payload", JobInput)

    def test_returns_none_for_non_model_tool(self) -> None:
        assert get_single_model(_no_models) is None

    def test_returns_none_for_multiple_model_params(self) -> None:
        assert get_single_model(_two_model_params) is None

    def test_returns_none_for_mixed_params(self) -> None:
        assert get_single_model(_mixed_params) is None

    def test_context_param_is_not_counted(self) -> None:
        result = get_single_model(_single_model_with_context)

        assert result == ("payload", JobInput)

    def test_annotated_model_is_detected(self) -> None:
        result = get_single_model(_annotated_model_param)

        assert result == ("payload", JobInput)


class TestSingleModelSchema:
    def test_schema_is_the_model_schema(self) -> None:
        schema = build_canonical_schema(_single_model_tool)
        properties = schema.get("properties", {})

        assert "name" in properties
        assert "count" in properties
        assert properties["name"]["type"] == "string"

    def test_schema_excludes_context(self) -> None:
        schema = build_canonical_schema(_single_model_with_context)

        assert set(schema.get("properties", {}).keys()) == {"name", "count"}


class TestSingleModelValidation:
    def test_valid_args_yield_model_instance(self) -> None:
        validate = build_validator(_single_model_tool)

        result = validate({"payload": {"name": "j", "count": 2}})

        assert isinstance(result["payload"], JobInput)
        assert result["payload"].name == "j"
        assert result["payload"].count == 2

    def test_invalid_args_raise_tool_validation_error(self) -> None:
        validate = build_validator(_single_model_tool)

        with pytest.raises(ToolValidationError):
            validate({"payload": {"name": "j", "count": 0}})

    def test_model_instance_passes_through(self) -> None:
        validate = build_validator(_single_model_tool)
        instance = JobInput(name="j", count=3)

        result = validate({"payload": instance})

        assert result["payload"] is instance


class TestSingleModelTool:
    def test_invoke_flattens_args_into_model(self) -> None:
        wrapped = Tool(_single_model_tool, _spec())

        result = wrapped.invoke({"name": "alpha", "count": 4})

        assert result == "alphax4"

    def test_invoke_with_context_injects_context(self) -> None:
        wrapped = Tool(_single_model_with_context, _spec())
        ctx = Context(trace_id="t-1")

        result = wrapped.invoke({"name": "j", "count": 1}, context=ctx)

        assert result == "j [t-1]"

    def test_invoke_raises_validation_on_bad_input(self) -> None:
        wrapped = Tool(_single_model_tool, _spec())

        with pytest.raises(ToolValidationError):
            wrapped.invoke({"name": "j", "count": -1})

    def test_async_single_model_invoke(self) -> None:
        wrapped = Tool(_single_model_async, _spec())

        result = asyncio.run(wrapped.invoke({"name": "a", "count": 2}))

        assert result == "a-2"

    def test_direct_call_with_model_instance(self) -> None:
        wrapped = Tool(_single_model_tool, _spec())

        assert wrapped(JobInput(name="x", count=5)) == "xx5"

    def test_get_schema_returns_model_schema(self) -> None:
        wrapped = Tool(_single_model_tool, _spec())
        schema = wrapped.get_schema()

        assert "name" in schema["properties"]
        assert "count" in schema["properties"]
