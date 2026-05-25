"""Tests for the tool registry and ``tool_scope``."""

from __future__ import annotations

import asyncio

import pytest

from phronesis.tools.decorator import tool
from phronesis.tools.errors import DuplicateToolError, ToolNotFoundError
from phronesis.tools.registry import (
    _global_registry,
    current_registry,
    tool_scope,
)
from phronesis.tools.spec import ToolSpec
from phronesis.tools.tool import Tool
from phronesis.tools.tool_id import ToolId, ToolName


def _make_tool(canonical: str, name: str = "echo") -> Tool:
    spec = ToolSpec(
        id=ToolId(canonical),
        name=ToolName(name),
        description="",
    )
    return Tool(lambda: None, spec)


class TestRegistration:
    def test_decorator_registers_in_current_registry(self) -> None:
        @tool(id="phronesis.tools.alpha")
        def alpha() -> None: ...

        assert current_registry().lookup("phronesis.tools.alpha") is alpha

    def test_lookup_by_tool_id_object(self) -> None:
        @tool(id="phronesis.tools.beta")
        def beta() -> None: ...

        assert current_registry().lookup(ToolId("phronesis.tools.beta")) is beta

    def test_lookup_unknown_raises_tool_not_found(self) -> None:
        with pytest.raises(ToolNotFoundError) as exc:
            current_registry().lookup("phronesis.tools.missing")

        assert exc.value.details["id"] == "phronesis.tools.missing"


class TestDuplicates:
    def test_duplicate_id_raises(self) -> None:
        @tool(id="phronesis.tools.dup")
        def first() -> None: ...

        with pytest.raises(DuplicateToolError) as exc:

            @tool(id="phronesis.tools.dup")
            def second() -> None: ...

        assert exc.value.details["id"] == "phronesis.tools.dup"

    def test_registering_same_tool_object_is_idempotent(self) -> None:
        registry = current_registry()
        built = _make_tool("phronesis.tools.idem")

        registry.register(built)
        registry.register(built)

        assert registry.lookup("phronesis.tools.idem") is built


class TestScopes:
    def test_tool_scope_isolates_from_global(self) -> None:
        with tool_scope() as scoped:

            @tool(id="phronesis.tools.scoped_only")
            def scoped_tool() -> None: ...

            assert scoped.lookup("phronesis.tools.scoped_only") is scoped_tool

        with pytest.raises(ToolNotFoundError):
            _global_registry.lookup("phronesis.tools.scoped_only")

    def test_exit_restores_previous_registry(self) -> None:
        outer = current_registry()

        with tool_scope() as inner:
            assert current_registry() is inner

        assert current_registry() is outer

    def test_nested_scopes_stack(self) -> None:
        with tool_scope() as outer:
            built_outer = _make_tool("phronesis.tools.outer")
            outer.register(built_outer)

            with tool_scope() as inner:
                built_inner = _make_tool("phronesis.tools.inner")
                inner.register(built_inner)

                assert inner.lookup("phronesis.tools.inner") is built_inner

                with pytest.raises(ToolNotFoundError):
                    inner.lookup("phronesis.tools.outer")

            assert outer.lookup("phronesis.tools.outer") is built_outer

            with pytest.raises(ToolNotFoundError):
                outer.lookup("phronesis.tools.inner")

    def test_concurrent_async_scopes_do_not_mix(self) -> None:
        async def declare(canonical: str) -> tuple[int, str]:
            with tool_scope() as scoped:
                built = _make_tool(canonical)
                scoped.register(built)

                await asyncio.sleep(0)

                return len(scoped.all()), scoped.lookup(canonical).spec.id.canonical

        async def main() -> list[tuple[int, str]]:
            return list(
                await asyncio.gather(
                    declare("phronesis.tools.a"),
                    declare("phronesis.tools.b"),
                    declare("phronesis.tools.c"),
                )
            )

        results = asyncio.run(main())

        assert results == [
            (1, "phronesis.tools.a"),
            (1, "phronesis.tools.b"),
            (1, "phronesis.tools.c"),
        ]


class TestRegistryOperations:
    def test_all_returns_registered_tools(self) -> None:
        registry = current_registry()
        a = _make_tool("phronesis.tools.list_a", "a")
        b = _make_tool("phronesis.tools.list_b", "b")
        registry.register(a)
        registry.register(b)

        assert set(registry.all()) == {a, b}

    def test_clear_empties_registry(self) -> None:
        registry = current_registry()
        registry.register(_make_tool("phronesis.tools.clear_me"))

        registry.clear()

        assert registry.all() == ()
