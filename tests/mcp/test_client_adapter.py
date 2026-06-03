"""Tests for the client-side MCP -> phronesis tool adapter."""

from __future__ import annotations

from typing import Any
from unittest.mock import AsyncMock

import mcp.types as mcp_types
import pytest

from phronesis.mcp._adapt import (
    mcp_tool_to_phronesis_tool,
    payload_to_content_blocks,
)
from phronesis.tools.errors import ToolError
from phronesis.tools.tool import Tool


class _FakeClient:
    """Minimal stand-in for :class:`McpClient` exposing a mocked session."""

    def __init__(self, call_result: mcp_types.CallToolResult | Exception) -> None:
        self._call_result = call_result
        self.session = AsyncMock()

        if isinstance(call_result, Exception):
            self.session.call_tool.side_effect = call_result
        else:
            self.session.call_tool.return_value = call_result


def _ok_text_result(text: str) -> mcp_types.CallToolResult:
    return mcp_types.CallToolResult(
        content=[mcp_types.TextContent(type="text", text=text)],
        isError=False,
    )


def _err_result(text: str) -> mcp_types.CallToolResult:
    return mcp_types.CallToolResult(
        content=[mcp_types.TextContent(type="text", text=text)],
        isError=True,
    )


def _mcp_tool(
    *,
    name: str = "echo",
    description: str | None = "Echo a string.",
    input_schema: dict[str, Any] | None = None,
) -> mcp_types.Tool:
    return mcp_types.Tool(
        name=name,
        description=description,
        inputSchema=input_schema or {"type": "object", "properties": {}},
    )


class TestAdaptShape:
    def test_returns_phronesis_tool(self) -> None:
        client = _FakeClient(_ok_text_result("ok"))

        tool = mcp_tool_to_phronesis_tool(client, _mcp_tool(), server_name="fs")  # type: ignore[arg-type]

        assert isinstance(tool, Tool)

    def test_preserves_name_and_description(self) -> None:
        client = _FakeClient(_ok_text_result("ok"))

        tool = mcp_tool_to_phronesis_tool(
            client,  # type: ignore[arg-type]
            _mcp_tool(name="search", description="Search docs."),
            server_name="fs",
        )

        assert str(tool.spec.name) == "search"
        assert tool.spec.description == "Search docs."

    def test_canonical_id_includes_server_and_name(self) -> None:
        client = _FakeClient(_ok_text_result("ok"))

        tool = mcp_tool_to_phronesis_tool(
            client,  # type: ignore[arg-type]
            _mcp_tool(name="read_file"),
            server_name="fs",
        )

        assert tool.spec.id.canonical == "phronesis.mcp.fs.read_file"

    def test_schema_mirrors_remote(self) -> None:
        schema = {
            "type": "object",
            "properties": {"path": {"type": "string"}},
            "required": ["path"],
        }
        client = _FakeClient(_ok_text_result("ok"))

        tool = mcp_tool_to_phronesis_tool(
            client,  # type: ignore[arg-type]
            _mcp_tool(input_schema=schema),
            server_name="fs",
        )

        assert tool.get_schema() == schema

    def test_handles_missing_description(self) -> None:
        client = _FakeClient(_ok_text_result("ok"))

        tool = mcp_tool_to_phronesis_tool(
            client,  # type: ignore[arg-type]
            _mcp_tool(description=None),
            server_name="fs",
        )

        assert tool.spec.description == ""


class TestAdaptInvoke:
    async def test_invokes_remote_session(self) -> None:
        client = _FakeClient(_ok_text_result("pong"))

        tool = mcp_tool_to_phronesis_tool(
            client,  # type: ignore[arg-type]
            _mcp_tool(name="ping"),
            server_name="fs",
        )

        result = await tool.invoke({"msg": "hi"})

        assert result == "pong"
        client.session.call_tool.assert_awaited_once_with(name="ping", arguments={"msg": "hi"})

    async def test_returns_structured_when_present(self) -> None:
        structured: dict[str, Any] = {"count": 3}
        client = _FakeClient(
            mcp_types.CallToolResult(
                content=[mcp_types.TextContent(type="text", text="{}")],
                structuredContent=structured,
                isError=False,
            )
        )

        tool = mcp_tool_to_phronesis_tool(
            client,  # type: ignore[arg-type]
            _mcp_tool(),
            server_name="fs",
        )

        assert await tool.invoke({}) == structured

    async def test_error_result_raises_tool_error(self) -> None:
        client = _FakeClient(_err_result("upstream blew up"))

        tool = mcp_tool_to_phronesis_tool(
            client,  # type: ignore[arg-type]
            _mcp_tool(name="boom"),
            server_name="fs",
        )

        with pytest.raises(ToolError) as caught:
            await tool.invoke({})

        assert "upstream blew up" in caught.value.message

    async def test_remote_exception_becomes_tool_error(self) -> None:
        client = _FakeClient(RuntimeError("network down"))

        tool = mcp_tool_to_phronesis_tool(
            client,  # type: ignore[arg-type]
            _mcp_tool(name="x"),
            server_name="fs",
        )

        with pytest.raises(ToolError) as caught:
            await tool.invoke({})

        assert "network down" in caught.value.message


class TestPayloadHelper:
    def test_string_passthrough(self) -> None:
        blocks = payload_to_content_blocks("hello")

        assert blocks[0].text == "hello"

    def test_none_becomes_empty(self) -> None:
        blocks = payload_to_content_blocks(None)

        assert blocks[0].text == ""

    def test_dict_is_json_encoded(self) -> None:
        blocks = payload_to_content_blocks({"a": 1})

        assert blocks[0].text == '{"a": 1}'

    def test_falls_back_to_str_for_unserialisable(self) -> None:
        class Weird:
            def __repr__(self) -> str:
                return "<weird>"

        blocks = payload_to_content_blocks(Weird())

        assert "weird" in blocks[0].text
