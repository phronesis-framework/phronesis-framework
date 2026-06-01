"""Tests for the "did you mean" hint added to :class:`ToolNotFoundError`."""

from __future__ import annotations

from phronesis.agents.loop import _build_tool_not_found
from phronesis.tools.decorator import tool


@tool(id="phronesis.tests.suggest.read_file")
def read_file() -> str:
    """Read the file."""
    return ""


@tool(id="phronesis.tests.suggest.write_file")
def write_file() -> str:
    """Write the file."""
    return ""


@tool(id="phronesis.tests.suggest.list_files")
def list_files() -> str:
    """List files."""
    return ""


_TOOLS = {
    "read_file": read_file,
    "write_file": write_file,
    "list_files": list_files,
}


class TestSuggestion:
    def test_typo_yields_close_match(self) -> None:
        err = _build_tool_not_found("read_files", _TOOLS)  # type: ignore[arg-type]

        assert "read_file" in err.details["suggestions"]
        assert "Did you mean" in err.message

    def test_no_close_match_lists_available(self) -> None:
        err = _build_tool_not_found("totally_unrelated_xyz", _TOOLS)  # type: ignore[arg-type]

        assert err.details["suggestions"] == []
        assert "Available tools" in err.message
        assert err.details["available"] == sorted(_TOOLS)

    def test_no_tools_explains(self) -> None:
        err = _build_tool_not_found("anything", {})

        assert "no tools bound" in err.message

    def test_details_include_requested_name(self) -> None:
        err = _build_tool_not_found("ghost", _TOOLS)  # type: ignore[arg-type]

        assert err.details["tool_name"] == "ghost"
