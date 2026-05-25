"""Tests for ``Annotated`` markers."""

from __future__ import annotations

from typing import Annotated

from pydantic import StringConstraints

from phronesis.tools.markers import Ge, Gt, Le, Lt, MaxLen, MinLen, Pattern
from phronesis.tools.schema import build_canonical_schema


def _takes_age(age: Annotated[int, Ge(0), Le(150)]) -> None: ...


def _takes_name(name: Annotated[str, MinLen(1), MaxLen(100)]) -> None: ...


def _takes_code(code: Annotated[str, Pattern(r"^[A-Z]{3}$")]) -> None: ...


def _takes_count(count: Annotated[int, Gt(0), Lt(10)]) -> None: ...


class TestPattern:
    def test_returns_string_constraints(self) -> None:
        constraint = Pattern(r"^x")

        assert isinstance(constraint, StringConstraints)
        assert constraint.pattern == "^x"


class TestMarkersInSchema:
    def test_ge_and_le_produce_minimum_and_maximum(self) -> None:
        schema = build_canonical_schema(_takes_age)

        assert schema["properties"]["age"]["minimum"] == 0
        assert schema["properties"]["age"]["maximum"] == 150

    def test_gt_and_lt_produce_exclusive_bounds(self) -> None:
        schema = build_canonical_schema(_takes_count)

        prop = schema["properties"]["count"]

        assert prop.get("exclusiveMinimum") == 0
        assert prop.get("exclusiveMaximum") == 10

    def test_min_len_and_max_len_produce_length_bounds(self) -> None:
        schema = build_canonical_schema(_takes_name)

        prop = schema["properties"]["name"]

        assert prop["minLength"] == 1
        assert prop["maxLength"] == 100

    def test_pattern_produces_pattern_key(self) -> None:
        schema = build_canonical_schema(_takes_code)

        assert schema["properties"]["code"]["pattern"] == r"^[A-Z]{3}$"
