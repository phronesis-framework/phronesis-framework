"""Tests for the LLM-facing ``ToolError`` hierarchy."""

from __future__ import annotations

import json

import httpx
import pytest
from pydantic import BaseModel, ValidationError

from phronesis.tools.errors import (
    DuplicateToolError,
    ToolError,
    ToolHTTPError,
    ToolNotFoundError,
    ToolPermissionError,
    ToolTimeoutError,
    ToolValidationError,
    UnsupportedProviderError,
    auto_map_exception,
)


class TestHierarchy:
    @pytest.mark.parametrize(
        "cls",
        [
            ToolValidationError,
            ToolNotFoundError,
            ToolTimeoutError,
            ToolPermissionError,
            DuplicateToolError,
            ToolHTTPError,
            UnsupportedProviderError,
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
            (DuplicateToolError, "duplicate_tool"),
            (ToolHTTPError, "tool_http_error"),
            (UnsupportedProviderError, "unsupported_provider"),
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


def _httpx_status_error(status_code: int) -> httpx.HTTPStatusError:
    request = httpx.Request("GET", "https://example.test/resource")
    response = httpx.Response(status_code=status_code, request=request)

    return httpx.HTTPStatusError(
        f"HTTP {status_code}",
        request=request,
        response=response,
    )


class _Model(BaseModel):
    x: int


def _pydantic_validation_error() -> ValidationError:
    try:
        _Model(x="not-an-int")  # type: ignore[arg-type]
    except ValidationError as exc:
        return exc

    raise AssertionError("expected ValidationError")


class TestAutoMapException:
    def test_tool_error_passes_through_unchanged(self) -> None:
        original = ToolValidationError("bad")

        mapped = auto_map_exception(original)

        assert mapped is original

    def test_file_not_found_maps_to_tool_not_found(self) -> None:
        exc = FileNotFoundError(2, "missing", "/tmp/missing.txt")

        mapped = auto_map_exception(exc)

        assert isinstance(mapped, ToolNotFoundError)
        assert mapped.details == {"path": "/tmp/missing.txt"}

    def test_permission_error_maps_to_tool_permission(self) -> None:
        exc = PermissionError(13, "denied", "/etc/shadow")

        mapped = auto_map_exception(exc)

        assert isinstance(mapped, ToolPermissionError)
        assert mapped.details == {"path": "/etc/shadow"}

    def test_builtin_timeout_maps_to_tool_timeout(self) -> None:
        exc = TimeoutError("too slow")

        mapped = auto_map_exception(exc)

        assert isinstance(mapped, ToolTimeoutError)

    def test_pydantic_validation_error_maps_to_tool_validation(self) -> None:
        exc = _pydantic_validation_error()

        mapped = auto_map_exception(exc)

        assert isinstance(mapped, ToolValidationError)
        assert "errors" in mapped.details

    def test_httpx_4xx_maps_to_tool_http_error(self) -> None:
        exc = _httpx_status_error(404)

        mapped = auto_map_exception(exc)

        assert isinstance(mapped, ToolHTTPError)
        assert mapped.details == {
            "status_code": 404,
            "url": "https://example.test/resource",
        }

    def test_httpx_5xx_is_not_mapped(self) -> None:
        exc = _httpx_status_error(500)

        mapped = auto_map_exception(exc)

        assert mapped is None

    def test_value_error_is_not_mapped(self) -> None:
        mapped = auto_map_exception(ValueError("nope"))

        assert mapped is None

    def test_runtime_error_is_not_mapped(self) -> None:
        mapped = auto_map_exception(RuntimeError("boom"))

        assert mapped is None
