"""Tests for the MCP transport descriptors."""

from __future__ import annotations

import dataclasses

import pytest

from phronesis.mcp.transport import HttpTransport, StdioTransport


class TestStdioTransport:
    def test_defaults(self) -> None:
        transport = StdioTransport(command="python")

        assert transport.command == "python"
        assert transport.args == ()
        assert dict(transport.env) == {}

    def test_frozen(self) -> None:
        transport = StdioTransport(command="python")

        with pytest.raises(dataclasses.FrozenInstanceError):
            transport.command = "node"  # type: ignore[misc]

    def test_carries_args_and_env(self) -> None:
        transport = StdioTransport(
            command="npx",
            args=("-y", "fs-server"),
            env={"NODE_ENV": "production"},
        )

        assert transport.args == ("-y", "fs-server")
        assert dict(transport.env) == {"NODE_ENV": "production"}


class TestHttpTransport:
    def test_defaults(self) -> None:
        transport = HttpTransport(url="https://example.com/mcp")

        assert transport.url == "https://example.com/mcp"
        assert dict(transport.headers) == {}

    def test_frozen(self) -> None:
        transport = HttpTransport(url="https://example.com/mcp")

        with pytest.raises(dataclasses.FrozenInstanceError):
            transport.url = "https://other.com"  # type: ignore[misc]

    def test_carries_headers(self) -> None:
        transport = HttpTransport(
            url="https://example.com/mcp",
            headers={"Authorization": "Bearer token"},
        )

        assert dict(transport.headers) == {"Authorization": "Bearer token"}
