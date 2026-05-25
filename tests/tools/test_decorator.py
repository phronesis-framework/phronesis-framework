"""Tests for the ``@tool`` decorator."""

from __future__ import annotations

import asyncio
import inspect

from phronesis.tools.decorator import tool
from phronesis.tools.effects import ToolEffect
from phronesis.tools.tool import Tool


@tool
def bare_decorated(x: int) -> int:
    return x + 1


@tool()
def parens_decorated(x: int) -> int:
    return x + 1


@tool(name="custom_name")
def renamed() -> int:
    return 1


@tool
def slugify() -> str:
    return ""


@tool
def my_fn() -> None: ...


@tool
def documented() -> None:
    """Returns nothing useful."""


@tool
def undocumented() -> None: ...


@tool
def no_effects() -> None: ...


@tool
def no_version() -> None: ...


@tool(id="phronesis.tools.custom")
def explicit_id() -> None: ...


@tool(description="explicit")
def overridden_description() -> None:
    """from docstring"""


@tool(effects=[ToolEffect.NETWORK, ToolEffect.EXPENSIVE])
def with_effects() -> None: ...


@tool(version="1.2.3")
def with_version() -> None: ...


def sync_original(a: int, b: str = "x") -> bool:
    return True


sync_decorated = tool(sync_original)


@tool
def add_sync(a: int, b: int) -> int:
    return a + b


@tool
async def add_async(a: int, b: int) -> int:
    return a + b


class TestDecoratorForms:
    def test_bare_decorator_returns_tool(self) -> None:
        assert isinstance(bare_decorated, Tool)
        assert bare_decorated(2) == 3

    def test_parenthesized_decorator_returns_tool(self) -> None:
        assert isinstance(parens_decorated, Tool)
        assert parens_decorated(2) == 3

    def test_decorator_with_kwargs_returns_tool(self) -> None:
        assert isinstance(renamed, Tool)


class TestDefaultInference:
    def test_name_defaults_to_function_name(self) -> None:
        assert str(slugify.spec.name) == "slugify"

    def test_id_defaults_to_module_qualname(self) -> None:
        assert my_fn.spec.id.canonical.endswith("my_fn")
        assert my_fn.spec.id.canonical == my_fn.spec.id.canonical.lower()

    def test_description_defaults_to_docstring(self) -> None:
        assert documented.spec.description == "Returns nothing useful."

    def test_description_is_empty_when_no_docstring(self) -> None:
        assert undocumented.spec.description == ""

    def test_effects_default_to_empty_frozenset(self) -> None:
        assert no_effects.spec.effects == frozenset()

    def test_version_defaults_to_initial(self) -> None:
        assert no_version.spec.version == "0.1.0"


class TestOverrides:
    def test_name_override(self) -> None:
        assert str(renamed.spec.name) == "custom_name"

    def test_id_override(self) -> None:
        assert explicit_id.spec.id.canonical == "phronesis.tools.custom"

    def test_description_override_wins_over_docstring(self) -> None:
        assert overridden_description.spec.description == "explicit"

    def test_effects_override(self) -> None:
        assert with_effects.spec.effects == frozenset({ToolEffect.NETWORK, ToolEffect.EXPENSIVE})

    def test_version_override(self) -> None:
        assert with_version.spec.version == "1.2.3"


class TestPreservesSignatureAndInvocability:
    def test_signature_preserved(self) -> None:
        assert inspect.signature(sync_decorated) == inspect.signature(sync_original)

    def test_sync_function_still_callable(self) -> None:
        assert add_sync(2, 3) == 5

    def test_async_function_still_awaitable(self) -> None:
        assert asyncio.run(add_async(2, 3)) == 5

    def test_is_async_flag_for_async_decorated(self) -> None:
        assert add_async.is_async is True

    def test_is_async_flag_for_sync_decorated(self) -> None:
        assert add_sync.is_async is False


@tool
def schema_eager(x: int) -> int:
    return x


@tool(lazy=True)
def schema_lazy(x: int) -> int:
    return x


class TestEagerCanonicalSchema:
    def test_eager_decoration_populates_input_schema(self) -> None:
        assert "x" in schema_eager.spec.input_schema.get("properties", {})

    def test_lazy_decoration_leaves_input_schema_empty(self) -> None:
        assert dict(schema_lazy.spec.input_schema) == {}

    def test_lazy_get_schema_builds_on_demand(self) -> None:
        built = schema_lazy.get_schema()

        assert "x" in built.get("properties", {})
