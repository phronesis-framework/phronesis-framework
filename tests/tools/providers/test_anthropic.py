"""Tests for :class:`AnthropicAdapter`."""

from __future__ import annotations

from phronesis.tools.providers.anthropic import AnthropicAdapter
from phronesis.tools.providers.base import ProviderAdapter
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


class TestAnthropicAdapter:
    def test_implements_provider_adapter_protocol(self) -> None:
        assert isinstance(AnthropicAdapter(), ProviderAdapter)

    def test_name_is_anthropic(self) -> None:
        assert AnthropicAdapter.name == "anthropic"

    def test_adapt_returns_expected_top_level_keys(self) -> None:
        result = AnthropicAdapter().adapt(_canonical(), spec=_spec())

        assert set(result.keys()) == {"name", "description", "input_schema"}

    def test_adapt_populates_name_and_description_from_spec(self) -> None:
        result = AnthropicAdapter().adapt(_canonical(), spec=_spec())

        assert result["name"] == "greet"
        assert result["description"] == "Greets a user by name."

    def test_adapt_preserves_canonical_properties(self) -> None:
        result = AnthropicAdapter().adapt(_canonical(), spec=_spec())

        assert result["input_schema"]["properties"] == {
            "name": {"type": "string", "description": "The user's name."},
        }
        assert result["input_schema"]["required"] == ["name"]

    def test_adapt_adds_additional_properties_false(self) -> None:
        result = AnthropicAdapter().adapt(_canonical(), spec=_spec())

        assert result["input_schema"]["additionalProperties"] is False

    def test_adapt_does_not_mutate_canonical_input(self) -> None:
        canonical = _canonical()

        AnthropicAdapter().adapt(canonical, spec=_spec())

        assert "additionalProperties" not in canonical

    def test_adapt_respects_existing_additional_properties_value(self) -> None:
        canonical = _canonical()
        canonical["additionalProperties"] = True

        result = AnthropicAdapter().adapt(canonical, spec=_spec())

        assert result["input_schema"]["additionalProperties"] is True
