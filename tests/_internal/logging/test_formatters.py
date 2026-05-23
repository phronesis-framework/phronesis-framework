"""Tests for StructuredFormatter and HumanReadableFormatter."""

from __future__ import annotations

import json
import logging
import re
import sys
from typing import Any

from phronesis._internal.logging import HumanReadableFormatter, StructuredFormatter


def _make_record(
    *,
    level: int = logging.INFO,
    msg: str = "hello",
    name: str = "phronesis.test",
    extras: dict[str, Any] | None = None,
    exc_info: Any = None,
) -> logging.LogRecord:
    record = logging.LogRecord(
        name=name,
        level=level,
        pathname=__file__,
        lineno=10,
        msg=msg,
        args=(),
        exc_info=exc_info,
    )

    if extras:
        for key, value in extras.items():
            setattr(record, key, value)

    return record


class TestStructuredFormatter:
    def test_emits_valid_json(self) -> None:
        output = StructuredFormatter().format(_make_record())
        parsed = json.loads(output)

        assert parsed["message"] == "hello"

    def test_includes_standard_fields(self) -> None:
        record = _make_record(level=logging.WARNING, msg="oops", name="phronesis.x")
        parsed = json.loads(StructuredFormatter().format(record))

        assert parsed["level"] == "WARNING"
        assert parsed["logger"] == "phronesis.x"
        assert parsed["message"] == "oops"
        assert "timestamp" in parsed

    def test_timestamp_is_iso_utc_with_milliseconds(self) -> None:
        parsed = json.loads(StructuredFormatter().format(_make_record()))

        assert re.match(r"^\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}\.\d{3}Z$", parsed["timestamp"])

    def test_extras_merged_at_top_level(self) -> None:
        record = _make_record(extras={"run_id": "r1", "agent_id": "a1"})
        parsed = json.loads(StructuredFormatter().format(record))

        assert parsed["run_id"] == "r1"
        assert parsed["agent_id"] == "a1"

    def test_exc_info_included_when_present(self) -> None:
        try:
            raise ValueError("boom")

        except ValueError:
            record = _make_record(level=logging.ERROR, exc_info=sys.exc_info())

        parsed = json.loads(StructuredFormatter().format(record))

        assert "exc_info" in parsed
        assert "ValueError" in parsed["exc_info"]


class TestHumanReadableFormatter:
    def test_single_line_when_no_exception(self) -> None:
        output = HumanReadableFormatter().format(_make_record())

        assert "\n" not in output

    def test_includes_extras_in_brackets(self) -> None:
        record = _make_record(extras={"run_id": "r1"})
        output = HumanReadableFormatter().format(record)

        assert "[run_id=r1]" in output

    def test_no_brackets_without_extras(self) -> None:
        output = HumanReadableFormatter().format(_make_record())

        assert "[" not in output and "]" not in output

    def test_exception_appended_on_following_line(self) -> None:
        try:
            raise ValueError("boom")

        except ValueError:
            record = _make_record(level=logging.ERROR, exc_info=sys.exc_info())

        output = HumanReadableFormatter().format(record)

        assert "\n" in output
        assert "ValueError" in output
