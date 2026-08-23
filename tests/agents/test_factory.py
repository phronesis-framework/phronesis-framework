"""Tests for :func:`build_agent`, the programmatic declaration path."""

from __future__ import annotations

import pytest

from phronesis.agents import AgentSpec, build_agent
from phronesis.agents.errors import AgentConfigurationError, DuplicateAgentError
from phronesis.agents.id import AgentId
from phronesis.agents.registry import agent_scope, current_registry
from phronesis.providers.protocol import LLMProvider


def _spec(provider: LLMProvider, canonical: str = "phronesis.agents.built") -> AgentSpec:
    return AgentSpec(
        id=AgentId(canonical),
        name="built",
        model=provider,
        system_prompt="be brief",
    )


class TestBuildAgent:
    def test_returns_agent_bound_to_spec(self, provider: LLMProvider) -> None:
        spec = _spec(provider)

        with agent_scope():
            built = build_agent(spec)

        assert built.spec is spec

    def test_registers_by_default(self, provider: LLMProvider) -> None:
        with agent_scope():
            built = build_agent(_spec(provider))

            assert current_registry().lookup("phronesis.agents.built") is built

    def test_register_false_skips_the_registry(self, provider: LLMProvider) -> None:
        with agent_scope():
            build_agent(_spec(provider), register=False)

            with pytest.raises(LookupError):
                current_registry().lookup("phronesis.agents.built")

    def test_duplicate_id_raises(self, provider: LLMProvider) -> None:
        with agent_scope():
            build_agent(_spec(provider))

            with pytest.raises(DuplicateAgentError):
                build_agent(_spec(provider))

    def test_invalid_spec_raises_before_registering(self) -> None:
        spec = AgentSpec(
            id=AgentId("phronesis.agents.invalid"),
            name="invalid",
            model=object(),  # type: ignore[arg-type]
            system_prompt="x",
        )

        with agent_scope():
            with pytest.raises(AgentConfigurationError):
                build_agent(spec)

            with pytest.raises(LookupError):
                current_registry().lookup("phronesis.agents.invalid")
