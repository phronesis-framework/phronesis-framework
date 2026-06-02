"""Tests for ``AgentId`` and ``agent_id_generator``."""

from __future__ import annotations

import pytest

from phronesis._internal.ids.id import Id
from phronesis.agents.id import AgentId, agent_id_generator


def _module_level_agent() -> None:
    """Sample function used by ``from_function`` tests."""


class TestAgentId:
    def test_prefix_is_aid(self) -> None:
        assert AgentId.prefix == "AID"

    def test_is_subclass_of_id(self) -> None:
        assert issubclass(AgentId, Id)

    def test_accepts_valid_canonical(self) -> None:
        aid = AgentId("phronesis.agents.researcher")

        assert aid.canonical == "phronesis.agents.researcher"

    def test_str_returns_canonical(self) -> None:
        aid = AgentId("phronesis.agents.researcher")

        assert str(aid) == "phronesis.agents.researcher"

    def test_short_has_aid_prefix(self) -> None:
        aid = AgentId("phronesis.agents.researcher")

        assert aid.short.startswith("AID-")
        assert len(aid.short) == len("AID-") + 8

    @pytest.mark.parametrize(
        "canonical",
        [
            "",
            "1.bad",
            "a..b",
            "X.y",
            "a.B",
            "a.b.",
            ".a.b",
        ],
    )
    def test_rejects_invalid_canonical(self, canonical: str) -> None:
        with pytest.raises(ValueError):
            AgentId(canonical)

    def test_is_frozen(self) -> None:
        aid = AgentId("phronesis.agents.x")

        with pytest.raises(AttributeError):
            aid.canonical = "other"  # type: ignore[misc]


class TestAgentIdGenerator:
    def test_from_function_uses_module_qualname_lowercased(self) -> None:
        aid = agent_id_generator.from_function(_module_level_agent)

        assert aid.canonical == f"{__name__.lower()}._module_level_agent"
        assert isinstance(aid, AgentId)

    def test_from_canonical_builds_agent_id(self) -> None:
        aid = agent_id_generator.from_canonical("phronesis.agents.x")

        assert isinstance(aid, AgentId)
        assert aid.canonical == "phronesis.agents.x"

    def test_from_canonical_rejects_invalid(self) -> None:
        with pytest.raises(ValueError):
            agent_id_generator.from_canonical("1.bad")
