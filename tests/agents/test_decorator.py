"""Tests for the ``@agent`` decorator."""

from __future__ import annotations

from dataclasses import dataclass

import pytest

from phronesis.agents.agent import Agent
from phronesis.agents.decorator import agent
from phronesis.agents.errors import AgentConfigurationError, DuplicateAgentError
from phronesis.agents.registry import agent_scope, current_registry
from phronesis.agents.validation import EmptySystemPromptWarning
from phronesis.providers.protocol import LLMProvider
from phronesis.tools.tool import Tool


@dataclass(frozen=True, slots=True)
class _Report:
    text: str


def _researcher() -> str:
    """Investigate things."""


def _writer() -> str:
    """You write concise summaries."""


def _empty_doc() -> str: ...


def _no_annotation():  # type: ignore[no-untyped-def]
    """hi"""


def _returns_report() -> _Report:
    """produce a report"""


class TestBasicDecoration:
    def test_returns_agent_instance(self, provider: LLMProvider) -> None:
        with agent_scope():
            built = agent(model=provider)(_researcher)

        assert isinstance(built, Agent)
        assert built.name == "_researcher"

    def test_docstring_becomes_system_prompt(self, provider: LLMProvider) -> None:
        with agent_scope():
            built = agent(model=provider)(_writer)

        assert built.spec.system_prompt == "You write concise summaries."

    def test_canonical_id_derives_from_function(self, provider: LLMProvider) -> None:
        with agent_scope():
            built = agent(model=provider)(_researcher)

        assert built.id.canonical.endswith("._researcher")


class TestOverrides:
    def test_explicit_name_overrides_function_name(self, provider: LLMProvider) -> None:
        with agent_scope():
            built = agent(model=provider, name="custom")(_researcher)

        assert built.name == "custom"

    def test_explicit_id_overrides_canonical(self, provider: LLMProvider) -> None:
        with agent_scope():
            built = agent(model=provider, id="phronesis.agents.custom")(_researcher)

        assert built.id.canonical == "phronesis.agents.custom"

    def test_explicit_system_prompt_overrides_docstring(self, provider: LLMProvider) -> None:
        with agent_scope():
            built = agent(model=provider, system_prompt="explicit")(_writer)

        assert built.spec.system_prompt == "explicit"

    def test_tools_are_attached(self, provider: LLMProvider, tool_a: Tool, tool_b: Tool) -> None:
        with agent_scope():
            built = agent(model=provider, tools=[tool_a, tool_b])(_researcher)

        assert built.spec.tools == (tool_a, tool_b)

    def test_description_and_version_stored(self, provider: LLMProvider) -> None:
        with agent_scope():
            built = agent(model=provider, description="desc", version="9.9.9")(_researcher)

        assert built.spec.description == "desc"
        assert built.spec.version == "9.9.9"

    def test_max_iterations_override(self, provider: LLMProvider) -> None:
        with agent_scope():
            built = agent(model=provider, max_iterations=3)(_researcher)

        assert built.spec.max_iterations == 3


class TestOutputTypeInference:
    def test_str_return_means_no_output_type(self, provider: LLMProvider) -> None:
        with agent_scope():
            built = agent(model=provider)(_researcher)

        assert built.spec.output_type is None

    def test_class_return_becomes_output_type(self, provider: LLMProvider) -> None:
        with agent_scope():
            built = agent(model=provider)(_returns_report)

        assert built.spec.output_type is _Report

    def test_missing_annotation_means_none(self, provider: LLMProvider) -> None:
        with agent_scope():
            built = agent(model=provider)(_no_annotation)

        assert built.spec.output_type is None

    def test_explicit_output_type_overrides_annotation(self, provider: LLMProvider) -> None:
        with agent_scope():
            built = agent(model=provider, output_type=_Report)(_researcher)

        assert built.spec.output_type is _Report


class TestRegistration:
    def test_decorated_agent_is_registered(self, provider: LLMProvider) -> None:
        with agent_scope() as scope:
            built = agent(model=provider)(_researcher)

            assert scope.lookup(built.id) is built

    def test_duplicate_id_raises(self, provider: LLMProvider) -> None:
        with agent_scope():
            agent(model=provider, id="phronesis.agents.dup")(_researcher)

            with pytest.raises(DuplicateAgentError):
                agent(model=provider, id="phronesis.agents.dup")(_writer)


class TestValidationIntegration:
    def test_invalid_max_iterations_rejected(self, provider: LLMProvider) -> None:
        with agent_scope(), pytest.raises(AgentConfigurationError):
            agent(model=provider, max_iterations=0)(_researcher)

    def test_empty_docstring_warns(self, provider: LLMProvider) -> None:
        with agent_scope(), pytest.warns(EmptySystemPromptWarning):
            agent(model=provider)(_empty_doc)


class TestGlobalRegistrySideEffect:
    def test_decoration_outside_scope_registers_globally(self, provider: LLMProvider) -> None:
        registry = current_registry()

        built = agent(model=provider, id="phronesis.agents.global_one")(_researcher)

        try:
            assert registry.lookup("phronesis.agents.global_one") is built
        finally:
            registry.clear()
