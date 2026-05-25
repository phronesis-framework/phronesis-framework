"""Tests for ``phronesis.providers.openai.tools``."""

from __future__ import annotations

from types import MappingProxyType
from typing import Any

from phronesis.providers.openai.tools import to_openai_tool, to_openai_tools
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


class TestToOpenaiTool:
    def test_envelope_shape(self) -> None:
        spec = _spec()

        result = to_openai_tool(spec)

        assert result["type"] == "function"
        assert isinstance(result["function"], dict)

    def test_includes_name_and_parameters(self) -> None:
        spec = _spec(
            input_schema={"type": "object", "properties": {"q": {"type": "string"}}},
        )

        function = to_openai_tool(spec)["function"]

        assert function["name"] == "search"
        assert function["parameters"] == {
            "type": "object",
            "properties": {"q": {"type": "string"}},
        }

    def test_includes_description_when_present(self) -> None:
        function = to_openai_tool(_spec(description="Search the web"))["function"]

        assert function["description"] == "Search the web"

    def test_omits_description_when_empty(self) -> None:
        function = to_openai_tool(_spec(description=""))["function"]

        assert "description" not in function

    def test_parameters_is_plain_dict(self) -> None:
        spec = _spec(input_schema={"type": "object"})

        parameters = to_openai_tool(spec)["function"]["parameters"]

        assert isinstance(parameters, dict)
        assert not isinstance(parameters, MappingProxyType)


class TestToOpenaiTools:
    def test_empty_input(self) -> None:
        assert to_openai_tools([]) == []

    def test_multiple_specs(self) -> None:
        specs = [_spec(name="a"), _spec(name="b")]

        result = to_openai_tools(specs)

        assert [tool["function"]["name"] for tool in result] == ["a", "b"]
