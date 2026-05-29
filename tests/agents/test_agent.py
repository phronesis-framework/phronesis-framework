"""Tests for the :class:`Agent` wrapper skeleton."""

from __future__ import annotations

from phronesis.agents.agent import Agent
from phronesis.agents.id import AgentId
from phronesis.agents.spec import AgentSpec
from phronesis.providers.protocol import LLMProvider


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
