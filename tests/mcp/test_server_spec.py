"""Tests for :class:`McpServerSpec`."""

from __future__ import annotations

import dataclasses

import pytest

from phronesis.mcp.ids import McpServerId
from phronesis.mcp.server_spec import McpServerSpec
from phronesis.mcp.transport import StdioTransport


class TestDefaultServerId:
    def test_derives_from_name(self) -> None:
        spec = McpServerSpec(
            name="filesystem",
            transport=StdioTransport(command="python"),
        )

        assert spec.server_id.canonical == "phronesis.mcp.servers.filesystem"

    def test_sanitises_invalid_chars(self) -> None:
        spec = McpServerSpec(
            name="My Filesystem!",
            transport=StdioTransport(command="python"),
        )

        assert spec.server_id.canonical == "phronesis.mcp.servers.my_filesystem"

    def test_prepends_underscore_when_starting_with_digit(self) -> None:
        spec = McpServerSpec(
            name="123tools",
            transport=StdioTransport(command="python"),
        )

        assert spec.server_id.canonical == "phronesis.mcp.servers._123tools"

    def test_empty_after_sanitisation_raises(self) -> None:
        with pytest.raises(ValueError):
            McpServerSpec(
                name="!!!",
                transport=StdioTransport(command="python"),
            )


class TestExplicitServerId:
    def test_preserves_provided_id(self) -> None:
        provided = McpServerId("custom.mcp.server.foo")
        spec = McpServerSpec(
            name="x",
            transport=StdioTransport(command="python"),
            server_id=provided,
        )

        assert spec.server_id is provided


class TestFrozen:
    def test_cannot_mutate(self) -> None:
        spec = McpServerSpec(
            name="x",
            transport=StdioTransport(command="python"),
        )

        with pytest.raises(dataclasses.FrozenInstanceError):
            spec.name = "y"  # type: ignore[misc]
