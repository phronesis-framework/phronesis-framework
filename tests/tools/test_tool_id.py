"""Tests for ``ToolId`` and ``ToolName``."""

from __future__ import annotations

import pytest

from phronesis._internal.ids.id import Id
from phronesis.tools.tool_id import ToolId, ToolName, tool_id_generator


def _module_level_tool() -> None:
    """Sample function used by ``infer_from_function`` tests."""


class TestToolId:
    def test_prefix_is_tid(self) -> None:
        assert ToolId.prefix == "TID"

    def test_is_subclass_of_id(self) -> None:
        assert issubclass(ToolId, Id)

    def test_accepts_valid_canonical(self) -> None:
        tid = ToolId("phronesis.tools.search_web")

        assert tid.canonical == "phronesis.tools.search_web"

    def test_str_returns_canonical(self) -> None:
        tid = ToolId("phronesis.tools.search_web")

        assert str(tid) == "phronesis.tools.search_web"

    def test_short_has_tid_prefix(self) -> None:
        tid = ToolId("phronesis.tools.search_web")

        assert tid.short.startswith("TID-")
        assert len(tid.short) == len("TID-") + 8

    @pytest.mark.parametrize(
        "canonical",
        [
            "",
            "1.bad",
            "a..b",
            "X.y",
            "a.B",
            "a.b.",
            ".a.b",
        ],
    )
    def test_rejects_invalid_canonical(self, canonical: str) -> None:
        with pytest.raises(ValueError):
            ToolId(canonical)

    def test_is_frozen(self) -> None:
        tid = ToolId("phronesis.tools.x")

        with pytest.raises(AttributeError):
            tid.canonical = "other"  # type: ignore[misc]


class TestToolName:
    def test_is_str_at_runtime(self) -> None:
        name = ToolName("search_web")

        assert isinstance(name, str)
        assert name == "search_web"


class TestToolIdGenerator:
    def test_from_function_uses_module_qualname_lowercased(self) -> None:
        tid = tool_id_generator.from_function(_module_level_tool)

        assert tid.canonical == f"{__name__.lower()}._module_level_tool"
        assert isinstance(tid, ToolId)

    def test_from_canonical_builds_tool_id(self) -> None:
        tid = tool_id_generator.from_canonical("phronesis.tools.x")

        assert isinstance(tid, ToolId)
        assert tid.canonical == "phronesis.tools.x"

    def test_from_canonical_rejects_invalid(self) -> None:
        with pytest.raises(ValueError):
            tool_id_generator.from_canonical("1.bad")
