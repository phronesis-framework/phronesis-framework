"""Tests for the server-side phronesis tool -> MCP definition adapter."""

from __future__ import annotations

import mcp.types as mcp_types

from phronesis.mcp._adapt import phronesis_tool_to_mcp_definition
from phronesis.tools import tool


@tool
def greet(name: str) -> str:
    """Greet someone."""
    return f"hello {name}"


@tool
def silent() -> None:
    return None


class TestPhronesisToolToMcpDefinition:
    def test_returns_mcp_tool(self) -> None:
        definition = phronesis_tool_to_mcp_definition(greet)

        assert isinstance(definition, mcp_types.Tool)

    def test_preserves_name(self) -> None:
        definition = phronesis_tool_to_mcp_definition(greet)

        assert definition.name == "greet"

    def test_preserves_description(self) -> None:
        definition = phronesis_tool_to_mcp_definition(greet)

        assert definition.description == "Greet someone."

    def test_input_schema_matches_get_schema(self) -> None:
        definition = phronesis_tool_to_mcp_definition(greet)

        assert definition.inputSchema == greet.get_schema()

    def test_handles_tool_with_no_description(self) -> None:
        definition = phronesis_tool_to_mcp_definition(silent)

        assert definition.description is None
