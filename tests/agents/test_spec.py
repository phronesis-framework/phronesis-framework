"""Tests for ``AgentSpec``."""

from __future__ import annotations

import pytest

from phronesis.agents.id import AgentId
from phronesis.agents.spec import AgentSpec
from phronesis.providers.protocol import LLMProvider
from phronesis.tools.tool import Tool


class TestDefaults:
    def test_tools_defaults_to_empty(self, provider: LLMProvider) -> None:
        spec = AgentSpec(
            id=AgentId("phronesis.agents.x"),
            name="x",
            model=provider,
            system_prompt="hi",
        )

        assert spec.tools == ()

    def test_description_defaults_to_empty(self, provider: LLMProvider) -> None:
        spec = AgentSpec(
            id=AgentId("phronesis.agents.x"),
            name="x",
            model=provider,
            system_prompt="hi",
        )

        assert spec.description == ""

    def test_output_type_defaults_to_none(self, provider: LLMProvider) -> None:
        spec = AgentSpec(
            id=AgentId("phronesis.agents.x"),
            name="x",
            model=provider,
            system_prompt="hi",
        )

        assert spec.output_type is None

    def test_max_iterations_defaults_to_twenty(self, provider: LLMProvider) -> None:
        spec = AgentSpec(
            id=AgentId("phronesis.agents.x"),
            name="x",
            model=provider,
            system_prompt="hi",
        )

        assert spec.max_iterations == 20

    def test_version_defaults_to_zero_one_zero(self, provider: LLMProvider) -> None:
        spec = AgentSpec(
            id=AgentId("phronesis.agents.x"),
            name="x",
            model=provider,
            system_prompt="hi",
        )

        assert spec.version == "0.1.0"


class TestRoundTrip:
    def test_tools_are_round_tripped(
        self,
        provider: LLMProvider,
        tool_a: Tool,
        tool_b: Tool,
    ) -> None:
        spec = AgentSpec(
            id=AgentId("phronesis.agents.x"),
            name="x",
            model=provider,
            system_prompt="hi",
            tools=(tool_a, tool_b),
        )

        assert spec.tools == (tool_a, tool_b)

    def test_output_type_round_trips(self, provider: LLMProvider) -> None:
        class Answer:
            pass

        spec = AgentSpec(
            id=AgentId("phronesis.agents.x"),
            name="x",
            model=provider,
            system_prompt="hi",
            output_type=Answer,
        )

        assert spec.output_type is Answer


class TestFrozen:
    def test_is_frozen(self, provider: LLMProvider) -> None:
        spec = AgentSpec(
            id=AgentId("phronesis.agents.x"),
            name="x",
            model=provider,
            system_prompt="hi",
        )

        with pytest.raises(AttributeError):
            spec.name = "other"  # type: ignore[misc]
