"""Tests for the LLM-facing ``ToolError`` hierarchy."""

from __future__ import annotations

import json

import pytest

from phronesis.tools.errors import (
    ToolError,
    ToolNotFoundError,
    ToolPermissionError,
    ToolTimeoutError,
    ToolValidationError,
)


class TestHierarchy:
    @pytest.mark.parametrize(
        "cls",
        [
            ToolValidationError,
            ToolNotFoundError,
            ToolTimeoutError,
            ToolPermissionError,
        ],
    )
    def test_subclasses_inherit_from_tool_error(self, cls: type[ToolError]) -> None:
        assert issubclass(cls, ToolError)

    def test_tool_error_is_an_exception(self) -> None:
        assert issubclass(ToolError, Exception)


class TestCodes:
    @pytest.mark.parametrize(
        ("cls", "code"),
        [
            (ToolError, "tool_error"),
            (ToolValidationError, "tool_validation_error"),
            (ToolNotFoundError, "tool_not_found"),
            (ToolTimeoutError, "tool_timeout"),
            (ToolPermissionError, "tool_permission_denied"),
        ],
    )
    def test_each_class_has_stable_code(self, cls: type[ToolError], code: str) -> None:
        assert cls.code == code

    def test_instance_inherits_class_code(self) -> None:
        err = ToolValidationError("bad arg")

        assert err.code == "tool_validation_error"


class TestMessage:
    def test_message_is_accessible_as_attribute(self) -> None:
        err = ToolError("boom")

        assert err.message == "boom"

    def test_message_is_accessible_via_str(self) -> None:
        err = ToolError("boom")

        assert str(err) == "boom"


class TestDetails:
    def test_default_details_is_empty_dict(self) -> None:
        err = ToolError("boom")

        assert err.details == {}

    def test_details_is_stored_when_provided(self) -> None:
        err = ToolValidationError("bad arg", details={"field": "x", "expected": "int"})

        assert err.details == {"field": "x", "expected": "int"}

    def test_details_is_copied_to_avoid_shared_state(self) -> None:
        payload = {"field": "x"}

        err = ToolError("boom", details=payload)
        payload["field"] = "mutated"

        assert err.details == {"field": "x"}


class TestSerialization:
    def test_to_dict_returns_expected_shape(self) -> None:
        err = ToolTimeoutError("took too long", details={"seconds": 30})

        assert err.to_dict() == {
            "error": "tool_timeout",
            "message": "took too long",
            "details": {"seconds": 30},
        }

    def test_to_dict_includes_empty_details_when_unset(self) -> None:
        err = ToolNotFoundError("missing")

        assert err.to_dict() == {
            "error": "tool_not_found",
            "message": "missing",
            "details": {},
        }

    def test_to_dict_is_json_serializable(self) -> None:
        err = ToolPermissionError("denied", details={"path": "/etc/shadow"})

        encoded = json.dumps(err.to_dict())

        assert json.loads(encoded) == {
            "error": "tool_permission_denied",
            "message": "denied",
            "details": {"path": "/etc/shadow"},
        }


class TestRaising:
    def test_can_be_raised_and_caught_as_tool_error(self) -> None:
        with pytest.raises(ToolError) as exc_info:
            raise ToolValidationError("nope")

        assert exc_info.value.code == "tool_validation_error"

    def test_can_be_raised_and_caught_as_specific_class(self) -> None:
        with pytest.raises(ToolTimeoutError):
            raise ToolTimeoutError("slow")
