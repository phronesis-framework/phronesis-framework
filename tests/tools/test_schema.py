"""Tests for canonical JSON schema generation."""

from __future__ import annotations

from enum import StrEnum
from typing import Annotated, Literal

from pydantic import BaseModel

from phronesis.context.context import Context
from phronesis.tools.schema import build_canonical_schema


def _basic(s: str, i: int, f: float, b: bool) -> None: ...


def _container_list(xs: list[int]) -> None: ...


def _container_dict(d: dict[str, int]) -> None: ...


def _optional_param(x: int | None = None) -> None: ...


def _literal_param(mode: Literal["a", "b"]) -> None: ...


class Status(StrEnum):
    OPEN = "open"
    CLOSED = "closed"


def _enum_param(status: Status) -> None: ...


def _google_docstring(name: str, age: int) -> None:
    """Do something.

    Args:
        name: The user's name.
        age: The user's age in years.

    Returns:
        Nothing.
    """


def _annotated_overrides_docstring(age: Annotated[int, "Edad explícita"]) -> None:
    """Doc.

    Args:
        age: from docstring.
    """


class _Nested(BaseModel):
    field: str


def _nested_model(payload: _Nested, tag: str) -> None: ...


def _with_context(ctx: Context, name: str) -> None: ...


def _only_context(ctx: Context) -> None: ...


class TestBasicTypes:
    def test_each_basic_type_maps_correctly(self) -> None:
        schema = build_canonical_schema(_basic)

        props = schema["properties"]

        assert props["s"]["type"] == "string"
        assert props["i"]["type"] == "integer"
        assert props["f"]["type"] == "number"
        assert props["b"]["type"] == "boolean"

    def test_all_required_when_no_defaults(self) -> None:
        schema = build_canonical_schema(_basic)

        assert set(schema["required"]) == {"s", "i", "f", "b"}


class TestContainers:
    def test_list_of_int(self) -> None:
        schema = build_canonical_schema(_container_list)

        prop = schema["properties"]["xs"]

        assert prop["type"] == "array"
        assert prop["items"]["type"] == "integer"

    def test_dict_of_str_to_int(self) -> None:
        schema = build_canonical_schema(_container_dict)

        prop = schema["properties"]["d"]

        assert prop["type"] == "object"
        assert prop["additionalProperties"]["type"] == "integer"


class TestOptional:
    def test_optional_drops_null_from_union(self) -> None:
        schema = build_canonical_schema(_optional_param)

        prop = schema["properties"]["x"]

        assert prop.get("type") == "integer"

        if "anyOf" in prop:
            assert all(variant.get("type") != "null" for variant in prop["anyOf"])

    def test_optional_param_not_in_required(self) -> None:
        schema = build_canonical_schema(_optional_param)

        assert "x" not in schema.get("required", [])


class TestLiteralAndEnum:
    def test_literal_produces_enum(self) -> None:
        schema = build_canonical_schema(_literal_param)

        assert schema["properties"]["mode"]["enum"] == ["a", "b"]

    def test_strenum_produces_enum(self) -> None:
        schema = build_canonical_schema(_enum_param)

        prop = schema["properties"]["status"]

        assert set(prop["enum"]) == {"open", "closed"}


class TestDescriptions:
    def test_google_docstring_args_become_descriptions(self) -> None:
        schema = build_canonical_schema(_google_docstring)

        props = schema["properties"]

        assert props["name"]["description"] == "The user's name."
        assert props["age"]["description"] == "The user's age in years."

    def test_annotated_string_overrides_docstring(self) -> None:
        schema = build_canonical_schema(_annotated_overrides_docstring)

        assert schema["properties"]["age"]["description"] == "Edad explícita"


class TestRefInlining:
    def test_nested_model_is_inlined(self) -> None:
        schema = build_canonical_schema(_nested_model)

        assert "$defs" not in schema

        prop = schema["properties"]["payload"]

        assert prop.get("type") == "object"
        assert "field" in prop.get("properties", {})


class TestContextFiltering:
    def test_context_param_is_excluded_from_properties(self) -> None:
        schema = build_canonical_schema(_with_context)

        assert "ctx" not in schema.get("properties", {})
        assert "name" in schema.get("properties", {})

    def test_context_param_is_excluded_from_required(self) -> None:
        schema = build_canonical_schema(_with_context)

        assert "ctx" not in schema.get("required", [])

    def test_only_context_param_yields_empty_properties(self) -> None:
        schema = build_canonical_schema(_only_context)

        assert schema.get("properties", {}) == {}
