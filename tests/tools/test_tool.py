"""Tests for the :class:`Tool` invocable wrapper."""

from __future__ import annotations

import asyncio
import inspect

import pytest

from phronesis.tools.errors import ToolValidationError
from phronesis.tools.spec import ToolSpec
from phronesis.tools.tool import Tool
from phronesis.tools.tool_id import ToolId, ToolName


def _spec() -> ToolSpec:
    return ToolSpec(
        id=ToolId("phronesis.tools.echo"),
        name=ToolName("echo"),
        description="Echoes input back.",
    )


def _double(x: int) -> int:
    return x * 2


async def _inc(x: int) -> int:
    return x + 1


def _sum(a: int, b: int = 10) -> int:
    return a + b


def _noop_sync() -> None: ...


async def _noop_async() -> None: ...


def _annotated(a: int, b: str = "x") -> bool:
    return True


def _documented() -> None:
    """Docstring."""


class TestToolInvocation:
    def test_sync_function_remains_callable(self) -> None:
        wrapped = Tool(_double, _spec())

        assert wrapped(3) == 6

    def test_async_function_returns_awaitable(self) -> None:
        wrapped = Tool(_inc, _spec())
        result = asyncio.run(wrapped(4))

        assert result == 5

    def test_kwargs_are_forwarded(self) -> None:
        wrapped = Tool(_sum, _spec())

        assert wrapped(1, b=2) == 3


class TestToolMetadata:
    def test_is_async_flag_for_sync_function(self) -> None:
        wrapped = Tool(_noop_sync, _spec())

        assert wrapped.is_async is False

    def test_is_async_flag_for_async_function(self) -> None:
        wrapped = Tool(_noop_async, _spec())

        assert wrapped.is_async is True

    def test_exposes_spec(self) -> None:
        spec = _spec()
        wrapped = Tool(_noop_sync, spec)

        assert wrapped.spec is spec


class TestToolPreservesSignature:
    def test_signature_matches_original(self) -> None:
        wrapped = Tool(_annotated, _spec())

        assert inspect.signature(wrapped) == inspect.signature(_annotated)

    def test_name_and_doc_preserved_via_update_wrapper(self) -> None:
        wrapped = Tool(_documented, _spec())

        assert wrapped.__name__ == "_documented"
        assert wrapped.__doc__ == "Docstring."

    def test_wrapped_attribute_points_to_original(self) -> None:
        wrapped = Tool(_noop_sync, _spec())

        assert wrapped.__wrapped__ is _noop_sync


class TestToolRepr:
    def test_repr_contains_id_and_name(self) -> None:
        wrapped = Tool(_noop_sync, _spec())

        text = repr(wrapped)

        assert "phronesis.tools.echo" in text
        assert "echo" in text


class TestToolValidation:
    def test_valid_args_invoke_function(self) -> None:
        wrapped = Tool(_sum, _spec())

        assert wrapped(2, 3) == 5

    def test_positional_and_keyword_are_bound_then_validated(self) -> None:
        wrapped = Tool(_sum, _spec())

        assert wrapped(2, b=4) == 6

    def test_wrong_type_raises_tool_validation_error(self) -> None:
        wrapped = Tool(_sum, _spec())

        with pytest.raises(ToolValidationError):
            wrapped("not a number", 3)

    def test_missing_required_raises_tool_validation_error(self) -> None:
        def needs_arg(a: int) -> int:
            return a

        wrapped = Tool(needs_arg, _spec())

        with pytest.raises(ToolValidationError):
            wrapped()

    def test_invalid_signature_binding_raises_tool_validation_error(self) -> None:
        wrapped = Tool(_sum, _spec())

        with pytest.raises(ToolValidationError):
            wrapped(1, 2, 3)

    def test_async_tool_validates_before_returning_coroutine(self) -> None:
        async def afn(x: int) -> int:
            return x + 1

        wrapped = Tool(afn, _spec())

        with pytest.raises(ToolValidationError):
            wrapped("bad")

    def test_async_tool_runs_when_valid(self) -> None:
        async def afn(x: int) -> int:
            return x + 1

        wrapped = Tool(afn, _spec())

        assert asyncio.run(wrapped(1)) == 2


def _schema_target(x: int) -> int:
    return x


class TestToolGetSchema:
    def test_returns_canonical_dict_without_provider(self) -> None:
        wrapped = Tool(_schema_target, _spec())

        schema = wrapped.get_schema()

        assert schema["properties"]["x"]["type"] == "integer"

    def test_second_call_returns_cached_object(self) -> None:
        wrapped = Tool(_schema_target, _spec())

        first = wrapped.get_schema()
        second = wrapped.get_schema()

        assert first is second

    def test_provider_argument_is_not_implemented_yet(self) -> None:
        wrapped = Tool(_schema_target, _spec())

        with pytest.raises(NotImplementedError):
            wrapped.get_schema(provider="anthropic")
