"""Tests for ``phronesis.providers.anthropic.tools``."""

from __future__ import annotations

from types import MappingProxyType
from typing import Any

from phronesis.providers.anthropic.tools import to_anthropic_tool, to_anthropic_tools
from phronesis.tools import ToolSpec
from phronesis.tools.tool_id import ToolName, tool_id_generator


def _spec(
    name: str = "search",
    description: str = "Search the web",
    input_schema: dict[str, Any] | None = None,
) -> ToolSpec:
    return ToolSpec(
        id=tool_id_generator.from_canonical(f"test.tools.{name}"),
        name=ToolName(name),
        description=description,
        input_schema=input_schema or {"type": "object", "properties": {}},
    )


class TestToAnthropicTool:
    def test_includes_name_and_input_schema(self) -> None:
        spec = _spec(input_schema={"type": "object", "properties": {"q": {"type": "string"}}})

        result = to_anthropic_tool(spec)

        assert result["name"] == "search"
        assert result["input_schema"] == {
            "type": "object",
            "properties": {"q": {"type": "string"}},
        }

    def test_includes_description_when_present(self) -> None:
        spec = _spec(description="Search the web")

        assert to_anthropic_tool(spec)["description"] == "Search the web"

    def test_omits_description_when_empty(self) -> None:
        spec = _spec(description="")

        assert "description" not in to_anthropic_tool(spec)

    def test_input_schema_is_plain_dict(self) -> None:
        spec = _spec(input_schema={"type": "object"})

        schema = to_anthropic_tool(spec)["input_schema"]

        assert isinstance(schema, dict)
        assert not isinstance(schema, MappingProxyType)


class TestToAnthropicTools:
    def test_empty_input(self) -> None:
        assert to_anthropic_tools([]) == []

    def test_multiple_specs(self) -> None:
        specs = [_spec(name="a"), _spec(name="b")]

        result = to_anthropic_tools(specs)

        assert [tool["name"] for tool in result] == ["a", "b"]
