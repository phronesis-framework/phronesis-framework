"""Tests for structural protocols.

``isinstance`` against a ``runtime_checkable`` Protocol only verifies
attribute presence, not signatures. Tests reflect that contract.
"""

from phronesis._internal.typing import Identifiable, JsonValue, SupportsJson


class TestSupportsJson:
    def test_class_with_to_json_satisfies(self) -> None:
        class Serialisable:
            def to_json(self) -> JsonValue:
                return {"k": "v"}

        instance = Serialisable()

        assert isinstance(instance, SupportsJson)
        assert instance.to_json() == {"k": "v"}

    def test_class_without_to_json_does_not_satisfy(self) -> None:
        class Plain:
            pass

        assert not isinstance(Plain(), SupportsJson)


class TestIdentifiable:
    def test_class_with_id_property_satisfies(self) -> None:
        class WithId:
            @property
            def id(self) -> str:
                return "abc"

        assert isinstance(WithId(), Identifiable)

    def test_class_without_id_does_not_satisfy(self) -> None:
        class Plain:
            pass

        assert not isinstance(Plain(), Identifiable)
