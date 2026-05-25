"""Tests for ``Context``."""

from __future__ import annotations

import logging
from dataclasses import FrozenInstanceError
from datetime import UTC, datetime
from types import MappingProxyType

import pytest

from phronesis.communication.session_id import SessionId
from phronesis.context import Budget, Context
from phronesis.core.agent_id import AgentId
from phronesis.runtime.run_id import RunId


class TestContextDefaults:
    def test_all_identifiers_default_to_none(self) -> None:
        ctx = Context()

        assert ctx.run_id is None
        assert ctx.agent_id is None
        assert ctx.trace_id is None
        assert ctx.session_id is None

    def test_logger_budget_and_deadline_default_to_none(self) -> None:
        ctx = Context()

        assert ctx.logger is None
        assert ctx.budget is None
        assert ctx.deadline is None

    def test_metadata_defaults_to_empty_mapping(self) -> None:
        ctx = Context()

        assert dict(ctx.metadata) == {}


class TestContextConstruction:
    def test_accepts_all_documented_fields(self) -> None:
        deadline = datetime(2030, 1, 1, tzinfo=UTC)
        logger = logging.getLogger("phronesis.test")
        budget = Budget(tokens_remaining=100)
        run_id = RunId("phronesis.runs.r_001")
        agent_id = AgentId("phronesis.agents.planner")
        session_id = SessionId("phronesis.sessions.s_001")

        ctx = Context(
            run_id=run_id,
            agent_id=agent_id,
            session_id=session_id,
            trace_id="0af7651916cd43dd8448eb211c80319c",
            logger=logger,
            budget=budget,
            deadline=deadline,
            metadata={"k": "v"},
        )

        assert ctx.run_id is run_id
        assert ctx.agent_id is agent_id
        assert ctx.session_id is session_id
        assert ctx.trace_id == "0af7651916cd43dd8448eb211c80319c"
        assert ctx.logger is logger
        assert ctx.budget is budget
        assert ctx.deadline == deadline
        assert ctx.metadata["k"] == "v"


class TestContextImmutability:
    def test_cannot_assign_to_run_id(self) -> None:
        ctx = Context(run_id=RunId("phronesis.runs.r_001"))

        with pytest.raises(FrozenInstanceError):
            ctx.run_id = RunId("phronesis.runs.r_002")  # type: ignore[misc]

    def test_cannot_assign_to_budget(self) -> None:
        ctx = Context()

        with pytest.raises(FrozenInstanceError):
            ctx.budget = Budget()  # type: ignore[misc]


class TestContextMetadata:
    def test_dict_input_is_wrapped_as_mapping_proxy(self) -> None:
        ctx = Context(metadata={"k": "v"})

        assert isinstance(ctx.metadata, MappingProxyType)

    def test_metadata_cannot_be_mutated_directly(self) -> None:
        ctx = Context(metadata={"k": "v"})

        with pytest.raises(TypeError):
            ctx.metadata["k"] = "other"  # type: ignore[index]

    def test_mutating_source_dict_does_not_affect_metadata(self) -> None:
        source: dict[str, str] = {"k": "v"}

        ctx = Context(metadata=source)
        source["k"] = "mutated"
        source["new"] = "x"

        assert ctx.metadata["k"] == "v"
        assert "new" not in ctx.metadata

    def test_already_proxied_mapping_is_kept_as_is(self) -> None:
        proxied = MappingProxyType({"k": "v"})

        ctx = Context(metadata=proxied)

        assert ctx.metadata is proxied
