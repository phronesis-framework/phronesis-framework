"""Tests for eager :class:`AgentSpec` validation."""

from __future__ import annotations

import warnings
from typing import Any

import pytest

from phronesis.agents.errors import AgentConfigurationError
from phronesis.agents.id import AgentId
from phronesis.agents.spec import AgentSpec
from phronesis.agents.validation import EmptySystemPromptWarning, validate_spec
from phronesis.providers.protocol import LLMProvider
from phronesis.tools.tool import Tool


def _spec(provider: LLMProvider, **overrides: Any) -> AgentSpec:
    base: dict[str, Any] = {
        "id": AgentId("phronesis.agents.x"),
        "name": "x",
        "model": provider,
        "system_prompt": "be helpful",
    }
    base.update(overrides)
    return AgentSpec(**base)


class TestModel:
    def test_rejects_object_that_is_not_a_provider(self) -> None:
        spec = AgentSpec(
            id=AgentId("phronesis.agents.x"),
            name="x",
            model="not a provider",  # type: ignore[arg-type]
            system_prompt="be helpful",
        )

        with pytest.raises(AgentConfigurationError) as info:
            validate_spec(spec)

        assert info.value.details["agent_id"] == "phronesis.agents.x"

    def test_accepts_fake_provider(self, provider: LLMProvider) -> None:
        validate_spec(_spec(provider))


class TestTools:
    def test_accepts_empty_tools(self, provider: LLMProvider) -> None:
        validate_spec(_spec(provider))

    def test_accepts_distinct_tools(
        self,
        provider: LLMProvider,
        tool_a: Tool,
        tool_b: Tool,
    ) -> None:
        validate_spec(_spec(provider, tools=(tool_a, tool_b)))

    def test_rejects_non_tool_entry(self, provider: LLMProvider) -> None:
        with pytest.raises(AgentConfigurationError):
            validate_spec(_spec(provider, tools=("not-a-tool",)))

    def test_rejects_duplicate_tools(
        self,
        provider: LLMProvider,
        tool_a: Tool,
    ) -> None:
        with pytest.raises(AgentConfigurationError) as info:
            validate_spec(_spec(provider, tools=(tool_a, tool_a)))

        assert info.value.details["tool_id"] == tool_a.spec.id.canonical


class TestOutputType:
    def test_accepts_none(self, provider: LLMProvider) -> None:
        validate_spec(_spec(provider, output_type=None))

    def test_accepts_class(self, provider: LLMProvider) -> None:
        class Answer:
            pass

        validate_spec(_spec(provider, output_type=Answer))

    def test_rejects_non_type(self, provider: LLMProvider) -> None:
        with pytest.raises(AgentConfigurationError):
            validate_spec(_spec(provider, output_type="str"))  # type: ignore[arg-type]


class TestMaxIterations:
    def test_accepts_positive(self, provider: LLMProvider) -> None:
        validate_spec(_spec(provider, max_iterations=1))

    @pytest.mark.parametrize("value", [0, -1, -100])
    def test_rejects_non_positive(self, provider: LLMProvider, value: int) -> None:
        with pytest.raises(AgentConfigurationError):
            validate_spec(_spec(provider, max_iterations=value))


class TestSystemPrompt:
    def test_non_empty_prompt_does_not_warn(self, provider: LLMProvider) -> None:
        with warnings.catch_warnings(record=True) as captured:
            warnings.simplefilter("always")
            validate_spec(_spec(provider, system_prompt="be helpful"))

        assert not [w for w in captured if isinstance(w.message, EmptySystemPromptWarning)]

    def test_empty_prompt_warns(self, provider: LLMProvider) -> None:
        with pytest.warns(EmptySystemPromptWarning):
            validate_spec(_spec(provider, system_prompt=""))

    def test_whitespace_only_prompt_warns(self, provider: LLMProvider) -> None:
        with pytest.warns(EmptySystemPromptWarning):
            validate_spec(_spec(provider, system_prompt="   \n  "))
