"""Smoke tests for the public API of :mod:`phronesis.tools` and :mod:`phronesis`."""

from __future__ import annotations

import asyncio
import importlib

import phronesis
import phronesis.tools as tools_pkg
from phronesis.context.context import Context as _CtxImpl
from phronesis.tools.decorator import tool as _tool_impl
from phronesis.tools.discover import discover as _discover_impl
from phronesis.tools.effects import ToolEffect as _ToolEffectImpl
from phronesis.tools.errors import (
    DuplicateToolError as _Duplicate,
)
from phronesis.tools.errors import (
    SchemaDegradationWarning as _Warn,
)
from phronesis.tools.errors import (
    ToolDefinitionError as _ToolDefImpl,
)
from phronesis.tools.errors import (
    ToolError as _ToolErrorImpl,
)
from phronesis.tools.errors import (
    ToolHTTPError as _HTTP,
)
from phronesis.tools.errors import (
    ToolNotFoundError as _NotFound,
)
from phronesis.tools.errors import (
    ToolPermissionError as _Perm,
)
from phronesis.tools.errors import (
    ToolTimeoutError as _Timeout,
)
from phronesis.tools.errors import (
    ToolValidationError as _Valid,
)
from phronesis.tools.errors import (
    UnsupportedProviderError as _Unsupported,
)
from phronesis.tools.errors import (
    auto_map_exception as _automap,
)
from phronesis.tools.registry import (
    current_registry as _cur_reg,
)
from phronesis.tools.registry import (
    tool_scope as _scope_impl,
)
from phronesis.tools.spec import ToolSpec as _ToolSpecImpl
from phronesis.tools.tool import Tool as _ToolImpl
from phronesis.tools.tool_id import ToolId as _ToolIdImpl
from phronesis.tools.tool_id import ToolName as _ToolNameImpl

_EXPECTED_TOOLS_NAMES = {
    "Context": _CtxImpl,
    "DuplicateToolError": _Duplicate,
    "SchemaDegradationWarning": _Warn,
    "Tool": _ToolImpl,
    "ToolDefinitionError": _ToolDefImpl,
    "ToolEffect": _ToolEffectImpl,
    "ToolError": _ToolErrorImpl,
    "ToolHTTPError": _HTTP,
    "ToolId": _ToolIdImpl,
    "ToolName": _ToolNameImpl,
    "ToolNotFoundError": _NotFound,
    "ToolPermissionError": _Perm,
    "ToolSpec": _ToolSpecImpl,
    "ToolTimeoutError": _Timeout,
    "ToolValidationError": _Valid,
    "UnsupportedProviderError": _Unsupported,
    "auto_map_exception": _automap,
    "current_registry": _cur_reg,
    "discover": _discover_impl,
    "tool": _tool_impl,
    "tool_scope": _scope_impl,
}

_EXPECTED_TOP_LEVEL_NAMES = {
    "Context": _CtxImpl,
    "ToolEffect": _ToolEffectImpl,
    "ToolError": _ToolErrorImpl,
    "discover": _discover_impl,
    "tool": _tool_impl,
    "tool_scope": _scope_impl,
}


class TestToolsPackageAll:
    def test_all_is_sorted_and_unique(self) -> None:
        names = list(tools_pkg.__all__)

        assert names == sorted(names)
        assert len(names) == len(set(names))

    def test_all_matches_expected_set(self) -> None:
        assert set(tools_pkg.__all__) == set(_EXPECTED_TOOLS_NAMES)

    def test_every_name_is_importable_from_package(self) -> None:
        module = importlib.import_module("phronesis.tools")

        for name in tools_pkg.__all__:
            assert getattr(module, name) is _EXPECTED_TOOLS_NAMES[name]


class TestTopLevelAll:
    def test_top_level_exposes_expected_tools_subset(self) -> None:
        for name, expected in _EXPECTED_TOP_LEVEL_NAMES.items():
            assert getattr(phronesis, name) is expected

    def test_top_level_all_includes_tool_names(self) -> None:
        for name in _EXPECTED_TOP_LEVEL_NAMES:
            assert name in phronesis.__all__

    def test_top_level_all_is_sorted_and_unique(self) -> None:
        names = list(phronesis.__all__)

        assert names == sorted(names)
        assert len(names) == len(set(names))


def _add(a: int, b: int) -> int:
    return a + b


async def _inc(x: int) -> int:
    return x + 1


def _greet(name: str, ctx: phronesis.Context) -> str:
    trace = ctx.trace_id or "?"
    return f"hi {name} [{trace}]"


def _boom() -> None:
    raise phronesis.ToolError("nope")


class TestPublicApiSmoke:
    def test_decorate_register_and_invoke_end_to_end(self) -> None:
        with phronesis.tool_scope() as scope:
            wrapped = phronesis.tool(_add)
            scope.register(wrapped)

            looked_up = scope.lookup(wrapped.spec.id)

            assert looked_up is wrapped
            assert looked_up.invoke({"a": 2, "b": 3}) == 5

    def test_async_tool_via_top_level_api(self) -> None:
        with phronesis.tool_scope():
            wrapped = phronesis.tool(_inc)

            assert asyncio.run(wrapped.invoke({"x": 4})) == 5

    def test_context_param_injection_via_top_level_api(self) -> None:
        with phronesis.tool_scope():
            wrapped = phronesis.tool(_greet)
            ctx = phronesis.Context(trace_id="t-1")

            assert wrapped.invoke({"name": "alice"}, context=ctx) == "hi alice [t-1]"

    def test_tool_error_is_shared_class(self) -> None:
        with phronesis.tool_scope():
            wrapped = phronesis.tool(_boom)

            try:
                wrapped.invoke({})
            except phronesis.ToolError as exc:
                assert exc.message == "nope"
            else:  # pragma: no cover - safety net
                raise AssertionError("expected ToolError")
