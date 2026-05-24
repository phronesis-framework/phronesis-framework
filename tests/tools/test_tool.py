"""Tests for the :class:`Tool` invocable wrapper."""

from __future__ import annotations

import asyncio
import inspect

import pytest

from phronesis.context.context import Context
from phronesis.tools.errors import (
    ToolError,
    ToolNotFoundError,
    ToolPermissionError,
    ToolValidationError,
    UnsupportedProviderError,
)
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


class TestToolGetSchemaProvider:
    def test_anthropic_returns_anthropic_shape(self) -> None:
        wrapped = Tool(_schema_target, _spec())

        schema = wrapped.get_schema(provider="anthropic")

        assert set(schema.keys()) == {"name", "description", "input_schema"}
        assert schema["name"] == "echo"

    def test_openai_returns_function_envelope(self) -> None:
        wrapped = Tool(_schema_target, _spec())

        schema = wrapped.get_schema(provider="openai")

        assert schema["type"] == "function"
        assert schema["function"]["name"] == "echo"

    def test_second_call_same_provider_returns_cached_object(self) -> None:
        wrapped = Tool(_schema_target, _spec())

        first = wrapped.get_schema(provider="anthropic")
        second = wrapped.get_schema(provider="anthropic")

        assert first is second

    def test_canonical_and_provider_schemas_are_distinct(self) -> None:
        wrapped = Tool(_schema_target, _spec())

        canonical = wrapped.get_schema()
        adapted = wrapped.get_schema(provider="anthropic")

        assert canonical is not adapted

    def test_unknown_provider_raises_unsupported_provider_error(self) -> None:
        wrapped = Tool(_schema_target, _spec())

        with pytest.raises(UnsupportedProviderError) as exc_info:
            wrapped.get_schema(provider="bogus")

        assert exc_info.value.details["provider"] == "bogus"
        assert "anthropic" in exc_info.value.details["available"]


class TestToolErrorChannel:
    def test_tool_error_propagates_unchanged(self) -> None:
        def raises_tool_error() -> None:
            raise ToolError("boom", details={"k": "v"})

        wrapped = Tool(raises_tool_error, _spec())

        with pytest.raises(ToolError) as exc_info:
            wrapped()

        assert exc_info.value.message == "boom"
        assert exc_info.value.details == {"k": "v"}

    def test_file_not_found_is_mapped(self) -> None:
        def raises_fnf() -> None:
            raise FileNotFoundError(2, "missing", "/tmp/x.txt")

        wrapped = Tool(raises_fnf, _spec())

        with pytest.raises(ToolNotFoundError) as exc_info:
            wrapped()

        assert exc_info.value.details == {"path": "/tmp/x.txt"}

    def test_permission_error_is_mapped(self) -> None:
        def raises_perm() -> None:
            raise PermissionError(13, "denied", "/etc/shadow")

        wrapped = Tool(raises_perm, _spec())

        with pytest.raises(ToolPermissionError):
            wrapped()

    def test_unlisted_exception_propagates(self) -> None:
        def raises_value() -> None:
            raise ValueError("not in allowlist")

        wrapped = Tool(raises_value, _spec())

        with pytest.raises(ValueError):
            wrapped()

    def test_async_tool_error_propagates_unchanged(self) -> None:
        async def raises_tool_error() -> None:
            raise ToolError("async boom")

        wrapped = Tool(raises_tool_error, _spec())

        with pytest.raises(ToolError) as exc_info:
            asyncio.run(wrapped())

        assert exc_info.value.message == "async boom"

    def test_async_file_not_found_is_mapped(self) -> None:
        async def raises_fnf() -> None:
            raise FileNotFoundError(2, "missing", "/tmp/y.txt")

        wrapped = Tool(raises_fnf, _spec())

        with pytest.raises(ToolNotFoundError):
            asyncio.run(wrapped())

    def test_async_cancellation_always_propagates(self) -> None:
        async def gets_cancelled() -> None:
            raise asyncio.CancelledError

        wrapped = Tool(gets_cancelled, _spec())

        with pytest.raises(asyncio.CancelledError):
            asyncio.run(wrapped())

    def test_async_unlisted_exception_propagates(self) -> None:
        async def raises_value() -> None:
            raise ValueError("nope")

        wrapped = Tool(raises_value, _spec())

        with pytest.raises(ValueError):
            asyncio.run(wrapped())


def _greet(name: str, ctx: Context) -> str:
    trace = ctx.trace_id or "no-trace"
    return f"hello {name} [{trace}]"


async def _greet_async(name: str, ctx: Context) -> str:
    trace = ctx.trace_id or "no-trace"
    return f"hello {name} [{trace}]"


def _no_context_tool(x: int) -> int:
    return x + 1


class TestToolContextInjection:
    def test_invoke_injects_context(self) -> None:
        wrapped = Tool(_greet, _spec())
        ctx = Context(trace_id="abc")

        result = wrapped.invoke({"name": "alice"}, context=ctx)

        assert result == "hello alice [abc]"

    def test_invoke_async_injects_context(self) -> None:
        wrapped = Tool(_greet_async, _spec())
        ctx = Context(trace_id="xyz")

        result = asyncio.run(wrapped.invoke({"name": "bob"}, context=ctx))

        assert result == "hello bob [xyz]"

    def test_invoke_without_context_omits_injection(self) -> None:
        wrapped = Tool(_greet, _spec())

        with pytest.raises(TypeError):
            wrapped.invoke({"name": "alice"})

    def test_invoke_on_tool_without_context_param(self) -> None:
        wrapped = Tool(_no_context_tool, _spec())

        assert wrapped.invoke({"x": 1}) == 2

    def test_direct_call_does_not_auto_inject_context(self) -> None:
        wrapped = Tool(_greet, _spec())

        with pytest.raises(TypeError):
            wrapped(name="alice")

    def test_direct_call_accepts_context_as_kwarg(self) -> None:
        wrapped = Tool(_greet, _spec())
        ctx = Context(trace_id="direct")

        assert wrapped(name="alice", ctx=ctx) == "hello alice [direct]"

    def test_context_param_name_is_detected(self) -> None:
        wrapped = Tool(_greet, _spec())

        assert wrapped._context_param == "ctx"

    def test_no_context_param_when_absent(self) -> None:
        wrapped = Tool(_no_context_tool, _spec())

        assert wrapped._context_param is None
