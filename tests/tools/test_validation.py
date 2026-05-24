"""Tests for the Pydantic-backed argument validator."""

from __future__ import annotations

from enum import StrEnum
from typing import Any, Literal

import pytest

from phronesis.context.context import Context
from phronesis.tools.errors import ToolValidationError
from phronesis.tools.validation import build_validator


def _validator(fn: Any) -> Any:
    return build_validator(fn)


class Color(StrEnum):
    RED = "red"
    BLUE = "blue"


def _takes_color(x: Color) -> None: ...


class TestHappyPath:
    def test_valid_args_return_normalized_dict(self) -> None:
        def fn(a: int, b: str) -> None: ...

        result = _validator(fn)({"a": 1, "b": "x"})

        assert result == {"a": 1, "b": "x"}

    def test_no_params_returns_empty_dict(self) -> None:
        def fn() -> None: ...

        assert _validator(fn)({}) == {}

    def test_defaults_are_applied(self) -> None:
        def fn(a: int, b: int = 10) -> None: ...

        assert _validator(fn)({"a": 1}) == {"a": 1, "b": 10}


class TestBasicTypes:
    @pytest.mark.parametrize(
        ("annotation", "value"),
        [
            (str, "x"),
            (int, 1),
            (float, 1.5),
            (bool, True),
        ],
    )
    def test_each_basic_type_validates(self, annotation: type, value: Any) -> None:
        def fn(x: Any) -> None: ...

        fn.__annotations__ = {"x": annotation}

        assert _validator(fn)({"x": value}) == {"x": value}


class TestContainers:
    def test_list_of_int(self) -> None:
        def fn(xs: list[int]) -> None: ...

        assert _validator(fn)({"xs": [1, 2, 3]}) == {"xs": [1, 2, 3]}

    def test_dict_of_str_to_int(self) -> None:
        def fn(d: dict[str, int]) -> None: ...

        assert _validator(fn)({"d": {"a": 1}}) == {"d": {"a": 1}}

    def test_optional_accepts_none(self) -> None:
        def fn(x: int | None = None) -> None: ...

        assert _validator(fn)({"x": None}) == {"x": None}

    def test_optional_default_none(self) -> None:
        def fn(x: int | None = None) -> None: ...

        assert _validator(fn)({}) == {"x": None}


class TestLiteralAndEnum:
    def test_literal_accepts_member(self) -> None:
        def fn(x: Literal["a", "b"]) -> None: ...

        assert _validator(fn)({"x": "a"}) == {"x": "a"}

    def test_literal_rejects_non_member(self) -> None:
        def fn(x: Literal["a", "b"]) -> None: ...

        with pytest.raises(ToolValidationError):
            _validator(fn)({"x": "z"})

    def test_enum_accepts_string_value(self) -> None:
        result = _validator(_takes_color)({"x": "red"})

        assert result["x"] == Color.RED


class TestValidationErrors:
    def test_wrong_type_raises_with_field_and_schema(self) -> None:
        def fn(age: int) -> None: ...

        with pytest.raises(ToolValidationError) as exc:
            _validator(fn)({"age": "not a number"})

        assert exc.value.details["field"] == "age"
        assert exc.value.details["got_value"] == "not a number"
        assert exc.value.details["expected_schema"].get("type") == "integer"

    def test_missing_required_raises(self) -> None:
        def fn(a: int, b: int) -> None: ...

        with pytest.raises(ToolValidationError) as exc:
            _validator(fn)({"a": 1})

        assert exc.value.details["field"] == "b"

    def test_details_expected_schema_is_only_for_affected_field(self) -> None:
        def fn(a: int, b: str) -> None: ...

        with pytest.raises(ToolValidationError) as exc:
            _validator(fn)({"a": "bad", "b": "ok"})

        assert exc.value.details["field"] == "a"
        assert exc.value.details["expected_schema"].get("type") == "integer"
        assert "properties" not in exc.value.details["expected_schema"]


class TestVariadic:
    def test_var_positional_does_not_break_build(self) -> None:
        def fn(*args: int) -> None: ...

        assert _validator(fn)({}) == {}

    def test_var_keyword_does_not_break_build(self) -> None:
        def fn(**kwargs: int) -> None: ...

        assert _validator(fn)({}) == {}

    def test_regular_param_validated_alongside_variadic(self) -> None:
        def fn(a: int, *args: int, **kwargs: int) -> None: ...

        assert _validator(fn)({"a": 5}) == {"a": 5}


def _with_context(ctx: Context, name: str) -> None: ...


def _only_context(ctx: Context) -> None: ...


class TestContextFiltering:
    def test_context_param_is_not_required(self) -> None:
        assert _validator(_with_context)({"name": "alice"}) == {"name": "alice"}

    def test_only_context_param_validates_empty_dict(self) -> None:
        assert _validator(_only_context)({}) == {}
