"""Tests for ``_AgentRegistry``, ``current_registry`` and ``agent_scope``."""

from __future__ import annotations

import pytest

from phronesis.agents.agent import Agent
from phronesis.agents.errors import DuplicateAgentError
from phronesis.agents.id import AgentId
from phronesis.agents.registry import (
    AgentNotFoundError,
    _AgentRegistry,
    agent_scope,
    current_registry,
)
from phronesis.agents.spec import AgentSpec
from phronesis.providers.protocol import LLMProvider


def _agent(provider: LLMProvider, canonical: str, *, name: str | None = None) -> Agent:
    spec = AgentSpec(
        id=AgentId(canonical),
        name=name or canonical.rsplit(".", 1)[-1],
        model=provider,
        system_prompt="hi",
    )
    return Agent(spec)


class TestRegistryBasics:
    def test_register_then_lookup_by_id(self, provider: LLMProvider) -> None:
        registry = _AgentRegistry()

        agent = _agent(provider, "phronesis.agents.alpha")
        registry.register(agent)

        assert registry.lookup(agent.id) is agent

    def test_lookup_accepts_canonical_string(self, provider: LLMProvider) -> None:
        registry = _AgentRegistry()

        agent = _agent(provider, "phronesis.agents.alpha")
        registry.register(agent)

        assert registry.lookup("phronesis.agents.alpha") is agent

    def test_lookup_missing_raises(self) -> None:
        registry = _AgentRegistry()

        with pytest.raises(AgentNotFoundError):
            registry.lookup("phronesis.agents.missing")

    def test_all_returns_snapshot_tuple(self, provider: LLMProvider) -> None:
        registry = _AgentRegistry()

        registry.register(_agent(provider, "phronesis.agents.alpha"))
        registry.register(_agent(provider, "phronesis.agents.beta"))

        snapshot = registry.all()

        assert isinstance(snapshot, tuple)
        assert {a.id.canonical for a in snapshot} == {
            "phronesis.agents.alpha",
            "phronesis.agents.beta",
        }

    def test_clear_empties_the_registry(self, provider: LLMProvider) -> None:
        registry = _AgentRegistry()

        registry.register(_agent(provider, "phronesis.agents.alpha"))
        registry.clear()

        assert registry.all() == ()


class TestIdempotency:
    def test_register_same_instance_twice_is_a_noop(self, provider: LLMProvider) -> None:
        registry = _AgentRegistry()
        agent = _agent(provider, "phronesis.agents.alpha")

        registry.register(agent)
        registry.register(agent)

        assert registry.all() == (agent,)


class TestDuplicates:
    def test_distinct_agents_with_same_id_raise(self, provider: LLMProvider) -> None:
        registry = _AgentRegistry()

        first = _agent(provider, "phronesis.agents.alpha", name="one")
        second = _agent(provider, "phronesis.agents.alpha", name="two")

        registry.register(first)

        with pytest.raises(DuplicateAgentError) as info:
            registry.register(second)

        assert info.value.details["id"] == "phronesis.agents.alpha"
        assert info.value.details["existing_name"] == "one"
        assert info.value.details["incoming_name"] == "two"


class TestCurrentRegistry:
    def test_default_is_the_module_global(self) -> None:
        first = current_registry()
        second = current_registry()

        assert first is second


class TestAgentScope:
    def test_scope_isolates_registrations(self, provider: LLMProvider) -> None:
        outer = current_registry()

        with agent_scope() as scoped:
            assert current_registry() is scoped
            assert current_registry() is not outer

            scoped.register(_agent(provider, "phronesis.agents.alpha"))

            assert scoped.lookup("phronesis.agents.alpha") is not None

        assert current_registry() is outer

        with pytest.raises(AgentNotFoundError):
            outer.lookup("phronesis.agents.alpha")

    def test_scope_restores_previous_registry_on_exception(self) -> None:
        outer = current_registry()

        with pytest.raises(RuntimeError), agent_scope():
            raise RuntimeError("boom")

        assert current_registry() is outer
