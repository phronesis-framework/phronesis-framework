"""Tests for :class:`ToolVersion` and :func:`parse_version`."""

from __future__ import annotations

import pytest

from phronesis.tools.errors import ToolDefinitionError
from phronesis.tools.version import InvalidVersionError, ToolVersion, parse_version


class TestParseVersion:
    def test_parses_standard_triple(self) -> None:
        version = parse_version("1.2.3")

        assert version == ToolVersion(major=1, minor=2, patch=3)

    def test_parses_zero_components(self) -> None:
        version = parse_version("0.0.0")

        assert version == ToolVersion(major=0, minor=0, patch=0)

    def test_parses_multi_digit_components(self) -> None:
        version = parse_version("10.200.3000")

        assert version == ToolVersion(major=10, minor=200, patch=3000)

    @pytest.mark.parametrize(
        "bad",
        [
            "",
            "1",
            "1.2",
            "1.2.3.4",
            "1.2.x",
            "v1.2.3",
            "1.2.3-rc1",
            "1.2.3+build",
            " 1.2.3",
            "1.2.3 ",
            "-1.2.3",
            "1..3",
        ],
    )
    def test_rejects_malformed_strings(self, bad: str) -> None:
        with pytest.raises(InvalidVersionError):
            parse_version(bad)

    def test_rejects_non_string_input(self) -> None:
        with pytest.raises(InvalidVersionError) as exc_info:
            parse_version(123)  # type: ignore[arg-type]

        assert exc_info.value.details["value"] == 123


class TestToolVersionBehavior:
    def test_str_round_trips_with_parse(self) -> None:
        version = ToolVersion(major=2, minor=5, patch=7)

        assert parse_version(str(version)) == version

    def test_versions_are_ordered(self) -> None:
        assert ToolVersion(1, 0, 0) < ToolVersion(1, 0, 1)
        assert ToolVersion(1, 0, 9) < ToolVersion(1, 1, 0)
        assert ToolVersion(1, 9, 9) < ToolVersion(2, 0, 0)

    def test_versions_are_hashable(self) -> None:
        bucket = {ToolVersion(1, 0, 0), ToolVersion(1, 0, 0), ToolVersion(2, 0, 0)}

        assert len(bucket) == 2

    def test_versions_are_frozen(self) -> None:
        version = ToolVersion(1, 0, 0)

        with pytest.raises(AttributeError):
            version.major = 2  # type: ignore[misc]

    def test_uses_slots(self) -> None:
        assert hasattr(ToolVersion, "__slots__")
        assert not hasattr(ToolVersion(1, 0, 0), "__dict__")

    def test_negative_components_are_rejected(self) -> None:
        with pytest.raises(InvalidVersionError):
            ToolVersion(major=-1, minor=0, patch=0)

        with pytest.raises(InvalidVersionError):
            ToolVersion(major=0, minor=-1, patch=0)

        with pytest.raises(InvalidVersionError):
            ToolVersion(major=0, minor=0, patch=-1)


class TestErrorHierarchy:
    def test_invalid_version_error_is_a_tool_definition_error(self) -> None:
        assert issubclass(InvalidVersionError, ToolDefinitionError)

    def test_error_carries_offending_value(self) -> None:
        with pytest.raises(InvalidVersionError) as exc_info:
            parse_version("not.a.version")

        assert exc_info.value.details["value"] == "not.a.version"

    def test_error_code_is_stable(self) -> None:
        assert InvalidVersionError("bad").code == "invalid_tool_version"
