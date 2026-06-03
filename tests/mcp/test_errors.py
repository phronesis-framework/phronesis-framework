"""Tests for the MCP error hierarchy."""

from __future__ import annotations

from phronesis.errors import PhronesisError
from phronesis.mcp.errors import (
    McpConnectionError,
    McpError,
    McpProtocolError,
    McpTimeoutError,
    McpToolNotFoundError,
)


class TestHierarchy:
    def test_mcp_error_subclasses_phronesis_error(self) -> None:
        assert issubclass(McpError, PhronesisError)

    def test_all_subclasses_inherit_mcp_error(self) -> None:
        assert issubclass(McpConnectionError, McpError)
        assert issubclass(McpProtocolError, McpError)
        assert issubclass(McpTimeoutError, McpError)
        assert issubclass(McpToolNotFoundError, McpError)


class TestCodes:
    def test_base_code(self) -> None:
        assert McpError.code == "mcp_error"

    def test_connection_code(self) -> None:
        assert McpConnectionError.code == "mcp_connection_error"

    def test_protocol_code(self) -> None:
        assert McpProtocolError.code == "mcp_protocol_error"

    def test_timeout_code(self) -> None:
        assert McpTimeoutError.code == "mcp_timeout"

    def test_tool_not_found_code(self) -> None:
        assert McpToolNotFoundError.code == "mcp_tool_not_found"


class TestInstance:
    def test_carries_message_and_details(self) -> None:
        err = McpConnectionError("boom", details={"server": "x"})

        assert err.message == "boom"
        assert err.details == {"server": "x"}
        assert str(err) == "boom"
