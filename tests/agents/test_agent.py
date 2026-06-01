"""Tests for the :class:`Agent` wrapper skeleton."""

from __future__ import annotations

from phronesis.agents.agent import Agent
from phronesis.agents.id import AgentId
from phronesis.agents.spec import AgentSpec
from phronesis.context.default import DefaultContextBuilder
from phronesis.providers.protocol import LLMProvider
from phronesis.tools.tool import Tool


def _make_spec(provider: LLMProvider) -> AgentSpec:
    return AgentSpec(
        id=AgentId("phronesis.agents.x"),
        name="x",
        model=provider,
        system_prompt="hi",
    )


class TestConstruction:
    def test_holds_spec(self, provider: LLMProvider) -> None:
        spec = _make_spec(provider)

        agent = Agent(spec)

        assert agent.spec is spec

    def test_id_proxies_spec_id(self, provider: LLMProvider) -> None:
        spec = _make_spec(provider)

        agent = Agent(spec)

        assert agent.id is spec.id

    def test_name_proxies_spec_name(self, provider: LLMProvider) -> None:
        spec = _make_spec(provider)

        agent = Agent(spec)

        assert agent.name == "x"


class TestRepr:
    def test_repr_includes_id_and_name(self, provider: LLMProvider) -> None:
        spec = _make_spec(provider)

        agent = Agent(spec)

        text = repr(agent)

        assert "phronesis.agents.x" in text
        assert "x" in text


class TestWithProvider:
    def test_returns_new_agent(self, provider: LLMProvider) -> None:
        agent = Agent(_make_spec(provider))
        other = type(provider)()

        derived = agent.with_provider(other)

        assert derived is not agent

    def test_swaps_provider(self, provider: LLMProvider) -> None:
        agent = Agent(_make_spec(provider))
        other = type(provider)()

        derived = agent.with_provider(other)

        assert derived.spec.model is other

    def test_preserves_other_fields(self, provider: LLMProvider) -> None:
        agent = Agent(_make_spec(provider))
        other = type(provider)()

        derived = agent.with_provider(other)

        assert derived.spec.id == agent.spec.id
        assert derived.spec.name == agent.spec.name
        assert derived.spec.system_prompt == agent.spec.system_prompt

    def test_does_not_mutate_receiver(self, provider: LLMProvider) -> None:
        agent = Agent(_make_spec(provider))
        original_model = agent.spec.model
        other = type(provider)()

        _ = agent.with_provider(other)

        assert agent.spec.model is original_model


class TestWithTools:
    def test_replaces_tool_tuple(self, provider: LLMProvider, tool_a: Tool, tool_b: Tool) -> None:
        agent = Agent(_make_spec(provider))

        derived = agent.with_tools([tool_a, tool_b])

        assert derived.spec.tools == (tool_a, tool_b)

    def test_accepts_empty_sequence(self, provider: LLMProvider, tool_a: Tool) -> None:
        agent = Agent(_make_spec(provider)).with_tools([tool_a])

        derived = agent.with_tools([])

        assert derived.spec.tools == ()

    def test_returns_new_agent(self, provider: LLMProvider, tool_a: Tool) -> None:
        agent = Agent(_make_spec(provider))

        derived = agent.with_tools([tool_a])

        assert derived is not agent


class TestWithAddedTools:
    def test_appends_to_existing_tools(
        self, provider: LLMProvider, tool_a: Tool, tool_b: Tool
    ) -> None:
        agent = Agent(_make_spec(provider)).with_tools([tool_a])

        derived = agent.with_added_tools([tool_b])

        assert derived.spec.tools == (tool_a, tool_b)

    def test_preserves_order(self, provider: LLMProvider, tool_a: Tool, tool_b: Tool) -> None:
        agent = Agent(_make_spec(provider))

        derived = agent.with_added_tools([tool_b, tool_a])

        assert derived.spec.tools == (tool_b, tool_a)

    def test_does_not_mutate_receiver(self, provider: LLMProvider, tool_a: Tool) -> None:
        agent = Agent(_make_spec(provider))
        original_tools = agent.spec.tools

        _ = agent.with_added_tools([tool_a])

        assert agent.spec.tools == original_tools


class TestWithSystemPrompt:
    def test_swaps_prompt(self, provider: LLMProvider) -> None:
        agent = Agent(_make_spec(provider))

        derived = agent.with_system_prompt("new instructions")

        assert derived.spec.system_prompt == "new instructions"

    def test_accepts_empty_string(self, provider: LLMProvider) -> None:
        agent = Agent(_make_spec(provider))

        derived = agent.with_system_prompt("")

        assert derived.spec.system_prompt == ""


class TestWithMaxIterations:
    def test_swaps_cap(self, provider: LLMProvider) -> None:
        agent = Agent(_make_spec(provider))

        derived = agent.with_max_iterations(5)

        assert derived.spec.max_iterations == 5


class TestWithContextBuilder:
    def test_swaps_builder(self, provider: LLMProvider) -> None:
        agent = Agent(_make_spec(provider))
        new_builder = DefaultContextBuilder()

        derived = agent.with_context_builder(new_builder)

        assert derived.spec.context_builder is new_builder


class TestWithOutputType:
    def test_swaps_to_type(self, provider: LLMProvider) -> None:
        agent = Agent(_make_spec(provider))

        derived = agent.with_output_type(int)

        assert derived.spec.output_type is int

    def test_swaps_back_to_none(self, provider: LLMProvider) -> None:
        agent = Agent(_make_spec(provider)).with_output_type(int)

        derived = agent.with_output_type(None)

        assert derived.spec.output_type is None


class TestWithDescription:
    def test_swaps_description(self, provider: LLMProvider) -> None:
        agent = Agent(_make_spec(provider))

        derived = agent.with_description("a friendly bot")

        assert derived.spec.description == "a friendly bot"


class TestFluentChaining:
    def test_chained_with_calls_compose(
        self, provider: LLMProvider, tool_a: Tool, tool_b: Tool
    ) -> None:
        agent = Agent(_make_spec(provider))

        derived = (
            agent.with_tools([tool_a])
            .with_added_tools([tool_b])
            .with_max_iterations(7)
            .with_system_prompt("chained")
        )

        assert derived.spec.tools == (tool_a, tool_b)
        assert derived.spec.max_iterations == 7
        assert derived.spec.system_prompt == "chained"


class TestDescribe:
    def test_contains_name_and_id(self, provider: LLMProvider) -> None:
        agent = Agent(_make_spec(provider))

        text = agent.describe()

        assert "x" in text
        assert "phronesis.agents.x" in text

    def test_lists_tools(self, provider: LLMProvider, tool_a: Tool, tool_b: Tool) -> None:
        agent = Agent(_make_spec(provider)).with_tools([tool_a, tool_b])

        text = agent.describe()

        assert "alpha" in text
        assert "beta" in text

    def test_no_tools_shows_placeholder(self, provider: LLMProvider) -> None:
        agent = Agent(_make_spec(provider))

        text = agent.describe()

        assert "<none>" in text

    def test_includes_model_class_name(self, provider: LLMProvider) -> None:
        agent = Agent(_make_spec(provider))

        text = agent.describe()

        assert type(provider).__name__ in text

    def test_includes_max_iterations(self, provider: LLMProvider) -> None:
        agent = Agent(_make_spec(provider)).with_max_iterations(3)

        text = agent.describe()

        assert "3" in text

    def test_no_description_shows_placeholder(self, provider: LLMProvider) -> None:
        agent = Agent(_make_spec(provider))

        text = agent.describe()

        assert "<no description>" in text

    def test_description_shown_when_set(self, provider: LLMProvider) -> None:
        agent = Agent(_make_spec(provider)).with_description("hello world")

        text = agent.describe()

        assert "hello world" in text

    def test_truncates_long_system_prompt(self, provider: LLMProvider) -> None:
        long_prompt = "x" * 500
        agent = Agent(_make_spec(provider)).with_system_prompt(long_prompt)

        text = agent.describe()

        assert "\u2026" in text
        assert long_prompt not in text

    def test_output_type_free_form_default(self, provider: LLMProvider) -> None:
        agent = Agent(_make_spec(provider))

        text = agent.describe()

        assert "<free-form>" in text

    def test_output_type_class_name(self, provider: LLMProvider) -> None:
        agent = Agent(_make_spec(provider)).with_output_type(int)

        text = agent.describe()

        assert "int" in text
