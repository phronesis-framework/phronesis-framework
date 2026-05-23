"""Tests for JSON typing primitives.

These aliases are static-only; they have no runtime behaviour to assert.
The tests verify that the symbols are importable and that canonical
example values are assignable to each alias. Type correctness itself is
enforced by mypy in CI.
"""

from phronesis._internal.typing import JsonArray, JsonObject, JsonValue


class TestJsonArray:
    def test_accepts_mixed_primitive_values(self) -> None:
        value: JsonArray = [1, "two", 3.0, True, None]

        assert value == [1, "two", 3.0, True, None]

    def test_accepts_nested_arrays_and_objects(self) -> None:
        value: JsonArray = [[1, 2], {"k": "v"}]

        assert value[0] == [1, 2]
        assert value[1] == {"k": "v"}

    def test_accepts_empty(self) -> None:
        value: JsonArray = []

        assert value == []


class TestJsonObject:
    def test_accepts_primitive_values(self) -> None:
        value: JsonObject = {
            "s": "hello",
            "i": 1,
            "f": 1.5,
            "b": True,
            "n": None,
        }

        assert value["n"] is None

    def test_accepts_nested_objects_and_arrays(self) -> None:
        value: JsonObject = {"list": [1, 2], "obj": {"k": "v"}}

        assert value["list"] == [1, 2]
        assert value["obj"] == {"k": "v"}

    def test_accepts_empty(self) -> None:
        value: JsonObject = {}

        assert value == {}


class TestJsonValue:
    def test_accepts_each_primitive_variant(self) -> None:
        primitives: list[JsonValue] = ["s", 1, 1.5, True, None]

        assert primitives == ["s", 1, 1.5, True, None]

    def test_accepts_array(self) -> None:
        value: JsonValue = [1, 2, 3]

        assert value == [1, 2, 3]

    def test_accepts_object(self) -> None:
        value: JsonValue = {"k": "v"}

        assert value == {"k": "v"}

    def test_accepts_deeply_nested_structure(self) -> None:
        value: JsonValue = {
            "users": [
                {"id": 1, "name": "a", "tags": ["x", "y"]},
                {"id": 2, "name": "b", "tags": []},
            ],
            "count": 2,
            "ok": True,
            "meta": None,
        }

        assert isinstance(value, dict)
        assert value["count"] == 2
