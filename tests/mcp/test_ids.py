"""Tests for the MCP identifier types and their generators."""

from __future__ import annotations

import pytest

from phronesis.mcp.ids import (
    McpClientId,
    McpServerId,
    mcp_client_id_generator,
    mcp_server_id_generator,
)


class TestMcpServerId:
    def test_prefix_is_msid(self) -> None:
        identifier = McpServerId("phronesis.mcp.servers.filesystem")

        assert identifier.prefix == "MSID"

    def test_short_form_includes_prefix(self) -> None:
        identifier = McpServerId("phronesis.mcp.servers.filesystem")

        assert identifier.short.startswith("MSID-")
        assert len(identifier.short) == len("MSID-") + 8

    def test_invalid_canonical_raises(self) -> None:
        with pytest.raises(ValueError):
            McpServerId("Phronesis.MCP.Servers.X")


class TestMcpClientId:
    def test_prefix_is_mcid(self) -> None:
        identifier = McpClientId("phronesis.mcp.clients.filesystem")

        assert identifier.prefix == "MCID"

    def test_str_returns_canonical(self) -> None:
        identifier = McpClientId("phronesis.mcp.clients.x")

        assert str(identifier) == "phronesis.mcp.clients.x"


class TestGenerators:
    def test_server_generator_round_trips(self) -> None:
        canonical = "phronesis.mcp.servers.example"

        identifier = mcp_server_id_generator.from_canonical(canonical)

        assert isinstance(identifier, McpServerId)
        assert identifier.canonical == canonical

    def test_client_generator_round_trips(self) -> None:
        canonical = "phronesis.mcp.clients.example"

        identifier = mcp_client_id_generator.from_canonical(canonical)

        assert isinstance(identifier, McpClientId)
        assert identifier.canonical == canonical
