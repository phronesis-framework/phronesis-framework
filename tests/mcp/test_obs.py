"""Tests for the :func:`mcp_span` helper."""

from __future__ import annotations

from unittest.mock import patch

from phronesis.mcp.obs import mcp_span
from phronesis.obs.attributes import (
    MCP_OPERATION,
    MCP_SERVER_ID,
    MCP_TOOL_NAME,
)


class TestMcpSpan:
    async def test_emits_operation_attribute(self) -> None:
        captured: dict[str, object] = {}

        from contextlib import asynccontextmanager

        @asynccontextmanager
        async def fake_span(name, *, attributes):  # type: ignore[no-untyped-def]
            captured["name"] = name
            captured["attributes"] = attributes

            yield None

        with patch("phronesis.mcp.obs.start_span_async", fake_span):
            async with mcp_span("client.list_tools"):
                pass

        assert captured["name"] == "phronesis.mcp.client.list_tools"
        attrs = captured["attributes"]
        assert isinstance(attrs, dict)
        assert attrs[MCP_OPERATION] == "client.list_tools"

    async def test_extra_attributes_are_merged(self) -> None:
        captured: dict[str, object] = {}

        from contextlib import asynccontextmanager

        @asynccontextmanager
        async def fake_span(name, *, attributes):  # type: ignore[no-untyped-def]
            captured["attributes"] = attributes

            yield None

        with patch("phronesis.mcp.obs.start_span_async", fake_span):
            async with mcp_span(
                "server.call_tool",
                extra={
                    MCP_SERVER_ID: "phronesis.mcp.servers.math",
                    MCP_TOOL_NAME: "add",
                },
            ):
                pass

        attrs = captured["attributes"]
        assert isinstance(attrs, dict)
        assert attrs[MCP_SERVER_ID] == "phronesis.mcp.servers.math"
        assert attrs[MCP_TOOL_NAME] == "add"
        assert attrs[MCP_OPERATION] == "server.call_tool"
