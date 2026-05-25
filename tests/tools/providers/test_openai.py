"""Tests for :class:`OpenAIAdapter`."""

from __future__ import annotations

from phronesis.tools.providers.base import ProviderAdapter
from phronesis.tools.providers.openai import OpenAIAdapter
from phronesis.tools.spec import ToolSpec
from phronesis.tools.tool_id import ToolId, ToolName


def _spec() -> ToolSpec:
    return ToolSpec(
        id=ToolId("phronesis.tools.greet"),
        name=ToolName("greet"),
        description="Greets a user by name.",
    )


def _canonical() -> dict[str, object]:
    return {
        "type": "object",
        "properties": {
            "name": {"type": "string", "description": "The user's name."},
        },
        "required": ["name"],
    }


class TestOpenAIAdapter:
    def test_implements_provider_adapter_protocol(self) -> None:
        assert isinstance(OpenAIAdapter(), ProviderAdapter)

    def test_name_is_openai(self) -> None:
        assert OpenAIAdapter.name == "openai"

    def test_adapt_returns_function_envelope(self) -> None:
        result = OpenAIAdapter().adapt(_canonical(), spec=_spec())

        assert result["type"] == "function"
        assert set(result["function"].keys()) == {"name", "description", "parameters"}

    def test_adapt_populates_name_and_description_from_spec(self) -> None:
        result = OpenAIAdapter().adapt(_canonical(), spec=_spec())

        assert result["function"]["name"] == "greet"
        assert result["function"]["description"] == "Greets a user by name."

    def test_adapt_preserves_canonical_properties(self) -> None:
        result = OpenAIAdapter().adapt(_canonical(), spec=_spec())

        parameters = result["function"]["parameters"]

        assert parameters["properties"] == {
            "name": {"type": "string", "description": "The user's name."},
        }
        assert parameters["required"] == ["name"]

    def test_adapt_adds_additional_properties_false(self) -> None:
        result = OpenAIAdapter().adapt(_canonical(), spec=_spec())

        assert result["function"]["parameters"]["additionalProperties"] is False

    def test_adapt_does_not_mutate_canonical_input(self) -> None:
        canonical = _canonical()

        OpenAIAdapter().adapt(canonical, spec=_spec())

        assert "additionalProperties" not in canonical

    def test_adapt_respects_existing_additional_properties_value(self) -> None:
        canonical = _canonical()
        canonical["additionalProperties"] = True

        result = OpenAIAdapter().adapt(canonical, spec=_spec())

        assert result["function"]["parameters"]["additionalProperties"] is True
