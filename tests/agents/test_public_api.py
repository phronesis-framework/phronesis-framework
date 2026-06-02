"""Tests for the :mod:`phronesis.agents` public surface."""

from __future__ import annotations

import phronesis.agents as api


class TestPublicSurface:
    def test_all_names_resolve(self) -> None:
        for name in api.__all__:
            assert hasattr(api, name), f"{name} missing from phronesis.agents"

    def test_no_underscored_public_names(self) -> None:
        assert all(not name.startswith("_") for name in api.__all__)


class TestKeyReexports:
    def test_agent_decorator_is_exported(self) -> None:
        from phronesis.agents.decorator import agent as decorator_source

        assert api.agent is decorator_source

    def test_agent_class_is_exported(self) -> None:
        from phronesis.agents.agent import Agent as Source

        assert api.Agent is Source

    def test_session_is_exported(self) -> None:
        from phronesis.agents.session import Session as Source

        assert api.Session is Source

    def test_event_union_includes_every_event(self) -> None:
        union_args = api.AgentEvent.__args__  # type: ignore[attr-defined]
        member_names = {cls.__name__ for cls in union_args}

        assert member_names == {
            "RunStarted",
            "TextDelta",
            "ToolCallStarted",
            "ToolCallCompleted",
            "RunCompleted",
            "RunFailed",
        }


class TestErrorReexports:
    def test_error_hierarchy_intact(self) -> None:
        assert issubclass(api.AgentMaxIterationsError, api.AgentError)
        assert issubclass(api.AgentExecutionError, api.AgentError)
        assert issubclass(api.AgentConfigurationError, api.AgentError)
        assert issubclass(api.DuplicateAgentError, api.AgentConfigurationError)
