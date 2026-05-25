"""Tests for ``AgentId``."""

from __future__ import annotations

import pytest

from phronesis._internal.ids.id import Id
from phronesis.core.agent_id import AgentId, agent_id_generator


class TestAgentId:
    def test_prefix_is_aid(self) -> None:
        assert AgentId.prefix == "AID"

    def test_is_subclass_of_id(self) -> None:
        assert issubclass(AgentId, Id)

    def test_accepts_valid_canonical(self) -> None:
        aid = AgentId("phronesis.agents.planner")

        assert aid.canonical == "phronesis.agents.planner"

    def test_short_has_aid_prefix(self) -> None:
        aid = AgentId("phronesis.agents.planner")

        assert aid.short.startswith("AID-")
        assert len(aid.short) == len("AID-") + 8

    @pytest.mark.parametrize("canonical", ["", "1.bad", "a..b", "X.y"])
    def test_rejects_invalid_canonical(self, canonical: str) -> None:
        with pytest.raises(ValueError):
            AgentId(canonical)


class TestAgentIdGenerator:
    def test_from_canonical_builds_agent_id(self) -> None:
        aid = agent_id_generator.from_canonical("phronesis.agents.planner")

        assert isinstance(aid, AgentId)
        assert aid.canonical == "phronesis.agents.planner"

    def test_from_canonical_rejects_invalid(self) -> None:
        with pytest.raises(ValueError):
            agent_id_generator.from_canonical("1.bad")
