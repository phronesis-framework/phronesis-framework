"""Tests for the agent-side error hierarchy."""

from __future__ import annotations

import pytest

from phronesis.agents.errors import (
    AgentConfigurationError,
    AgentError,
    AgentExecutionError,
    AgentMaxIterationsError,
    AgentOutputValidationError,
    DuplicateAgentError,
)
from phronesis.errors import PhronesisError


class TestHierarchy:
    @pytest.mark.parametrize(
        "cls",
        [
            AgentMaxIterationsError,
            AgentOutputValidationError,
            AgentConfigurationError,
            AgentExecutionError,
        ],
    )
    def test_subclasses_inherit_from_agent_error(self, cls: type[AgentError]) -> None:
        assert issubclass(cls, AgentError)

    def test_agent_error_inherits_from_phronesis_error(self) -> None:
        assert issubclass(AgentError, PhronesisError)

    def test_duplicate_agent_error_is_configuration_error(self) -> None:
        assert issubclass(DuplicateAgentError, AgentConfigurationError)


class TestPhronesisErrorBase:
    def test_message_is_accessible_as_attribute(self) -> None:
        err = PhronesisError("boom")

        assert err.message == "boom"

    def test_message_is_accessible_via_str(self) -> None:
        err = PhronesisError("boom")

        assert str(err) == "boom"

    def test_default_details_is_empty_dict(self) -> None:
        err = PhronesisError("boom")

        assert err.details == {}

    def test_details_is_stored_when_provided(self) -> None:
        err = AgentConfigurationError("bad spec", details={"field": "model"})

        assert err.details == {"field": "model"}

    def test_details_is_copied_to_avoid_shared_state(self) -> None:
        payload = {"field": "model"}

        err = PhronesisError("boom", details=payload)
        payload["field"] = "mutated"

        assert err.details == {"field": "model"}


class TestRaiseAndCatch:
    def test_max_iterations_error_is_raisable(self) -> None:
        with pytest.raises(AgentMaxIterationsError):
            raise AgentMaxIterationsError("hit the cap")

    def test_output_validation_error_is_raisable(self) -> None:
        with pytest.raises(AgentOutputValidationError):
            raise AgentOutputValidationError("bad output")

    def test_configuration_error_is_raisable(self) -> None:
        with pytest.raises(AgentConfigurationError):
            raise AgentConfigurationError("invalid spec")

    def test_execution_error_can_wrap_a_cause(self) -> None:
        cause = RuntimeError("provider exploded")

        with pytest.raises(AgentExecutionError) as info:
            try:
                raise cause
            except RuntimeError as exc:
                raise AgentExecutionError("run aborted") from exc

        assert info.value.__cause__ is cause

    def test_duplicate_agent_caught_as_configuration(self) -> None:
        with pytest.raises(AgentConfigurationError):
            raise DuplicateAgentError("dup")

    def test_any_agent_error_caught_as_phronesis_error(self) -> None:
        with pytest.raises(PhronesisError):
            raise AgentMaxIterationsError("hit the cap")
