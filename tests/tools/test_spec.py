"""Tests for ``ToolSpec``."""

from __future__ import annotations

import json
from dataclasses import FrozenInstanceError
from types import MappingProxyType

import pytest

from phronesis.tools.effects import ToolEffect
from phronesis.tools.spec import ToolSpec
from phronesis.tools.tool_id import ToolId, ToolName


def _make_id() -> ToolId:
    return ToolId("phronesis.tools.echo")


def _make_name() -> ToolName:
    return ToolName("echo")


class TestToolSpecConstruction:
    def test_accepts_all_fields(self) -> None:
        spec = ToolSpec(
            id=_make_id(),
            name=_make_name(),
            description="Echoes input back.",
            effects=frozenset({ToolEffect.NETWORK}),
            input_schema={"type": "object"},
            output_schema={"type": "string"},
            version="1.2.3",
        )

        assert spec.id == _make_id()
        assert str(spec.name) == "echo"
        assert spec.description == "Echoes input back."
        assert spec.effects == frozenset({ToolEffect.NETWORK})
        assert spec.input_schema["type"] == "object"
        assert spec.output_schema is not None
        assert spec.output_schema["type"] == "string"
        assert spec.version == "1.2.3"


class TestToolSpecDefaults:
    def test_effects_default_to_empty(self) -> None:
        spec = ToolSpec(id=_make_id(), name=_make_name(), description="d")

        assert spec.effects == frozenset()

    def test_input_schema_defaults_to_empty(self) -> None:
        spec = ToolSpec(id=_make_id(), name=_make_name(), description="d")

        assert dict(spec.input_schema) == {}

    def test_output_schema_defaults_to_none(self) -> None:
        spec = ToolSpec(id=_make_id(), name=_make_name(), description="d")

        assert spec.output_schema is None

    def test_version_defaults_to_initial(self) -> None:
        spec = ToolSpec(id=_make_id(), name=_make_name(), description="d")

        assert spec.version == "0.1.0"


class TestToolSpecImmutability:
    def test_cannot_assign_to_description(self) -> None:
        spec = ToolSpec(id=_make_id(), name=_make_name(), description="d")

        with pytest.raises(FrozenInstanceError):
            spec.description = "other"  # type: ignore[misc]

    def test_cannot_assign_to_version(self) -> None:
        spec = ToolSpec(id=_make_id(), name=_make_name(), description="d")

        with pytest.raises(FrozenInstanceError):
            spec.version = "9.9.9"  # type: ignore[misc]


class TestToolSpecSchemaWrapping:
    def test_input_dict_is_wrapped_as_mapping_proxy(self) -> None:
        spec = ToolSpec(
            id=_make_id(),
            name=_make_name(),
            description="d",
            input_schema={"k": "v"},
        )

        assert isinstance(spec.input_schema, MappingProxyType)

    def test_output_dict_is_wrapped_as_mapping_proxy(self) -> None:
        spec = ToolSpec(
            id=_make_id(),
            name=_make_name(),
            description="d",
            output_schema={"k": "v"},
        )

        assert isinstance(spec.output_schema, MappingProxyType)

    def test_input_schema_cannot_be_mutated_directly(self) -> None:
        spec = ToolSpec(
            id=_make_id(),
            name=_make_name(),
            description="d",
            input_schema={"k": "v"},
        )

        with pytest.raises(TypeError):
            spec.input_schema["k"] = "other"  # type: ignore[index]

    def test_output_schema_cannot_be_mutated_directly(self) -> None:
        spec = ToolSpec(
            id=_make_id(),
            name=_make_name(),
            description="d",
            output_schema={"k": "v"},
        )

        assert spec.output_schema is not None

        with pytest.raises(TypeError):
            spec.output_schema["k"] = "other"  # type: ignore[index]

    def test_mutating_source_input_dict_does_not_affect_spec(self) -> None:
        source: dict[str, str] = {"k": "v"}

        spec = ToolSpec(
            id=_make_id(),
            name=_make_name(),
            description="d",
            input_schema=source,
        )
        source["k"] = "mutated"
        source["new"] = "x"

        assert spec.input_schema["k"] == "v"
        assert "new" not in spec.input_schema

    def test_mutating_source_output_dict_does_not_affect_spec(self) -> None:
        source: dict[str, str] = {"k": "v"}

        spec = ToolSpec(
            id=_make_id(),
            name=_make_name(),
            description="d",
            output_schema=source,
        )
        source["k"] = "mutated"

        assert spec.output_schema is not None
        assert spec.output_schema["k"] == "v"


class TestToolSpecToDict:
    def test_shape_with_all_fields(self) -> None:
        spec = ToolSpec(
            id=_make_id(),
            name=_make_name(),
            description="Echoes input back.",
            effects=frozenset({ToolEffect.NETWORK, ToolEffect.EXPENSIVE}),
            input_schema={"type": "object"},
            output_schema={"type": "string"},
            version="1.2.3",
        )

        data = spec.to_dict()

        assert data == {
            "id": "phronesis.tools.echo",
            "name": "echo",
            "description": "Echoes input back.",
            "effects": ["expensive", "network"],
            "input_schema": {"type": "object"},
            "output_schema": {"type": "string"},
            "version": "1.2.3",
        }

    def test_is_json_serializable(self) -> None:
        spec = ToolSpec(
            id=_make_id(),
            name=_make_name(),
            description="d",
            effects=frozenset({ToolEffect.NETWORK}),
            input_schema={"type": "object"},
        )

        payload = json.dumps(spec.to_dict())

        assert "phronesis.tools.echo" in payload

    def test_output_schema_none_emits_null(self) -> None:
        spec = ToolSpec(id=_make_id(), name=_make_name(), description="d")

        data = spec.to_dict()

        assert data["output_schema"] is None

    def test_effects_are_sorted_alphabetically(self) -> None:
        spec = ToolSpec(
            id=_make_id(),
            name=_make_name(),
            description="d",
            effects=frozenset(
                {
                    ToolEffect.NETWORK,
                    ToolEffect.EXPENSIVE,
                    ToolEffect.FILESYSTEM_READ,
                }
            ),
        )

        data = spec.to_dict()

        assert data["effects"] == ["expensive", "filesystem.read", "network"]


class TestToolSpecHasNoCallable:
    def test_spec_does_not_carry_function_reference(self) -> None:
        spec = ToolSpec(id=_make_id(), name=_make_name(), description="d")

        for field_name in (
            "id",
            "name",
            "description",
            "effects",
            "input_schema",
            "output_schema",
            "version",
        ):
            value = getattr(spec, field_name)

            assert not callable(value)
