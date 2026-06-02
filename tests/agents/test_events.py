"""Tests for the streaming :class:`AgentEvent` union."""

from __future__ import annotations

from types import MappingProxyType

import pytest

from phronesis.agents.errors import AgentMaxIterationsError
from phronesis.agents.events import (
    AgentEvent,
    RunCompleted,
    RunFailed,
    RunStarted,
    TextDelta,
    ToolCallCompleted,
    ToolCallStarted,
)
from phronesis.agents.id import AgentId
from phronesis.agents.run import Result, RunId, TokenUsage
from phronesis.tools.tool_id import ToolId


def _result() -> Result:
    return Result(
        run_id=RunId("phronesis.runtime.run.x"),
        output="done",
        tokens=TokenUsage(),
        iterations=1,
        tool_calls=(),
        messages=(),
    )


class TestRunStarted:
    def test_holds_run_and_agent_ids(self) -> None:
        rid = RunId("phronesis.runtime.run.x")
        aid = AgentId("phronesis.agents.x")

        event = RunStarted(run_id=rid, agent_id=aid)

        assert event.run_id is rid
        assert event.agent_id is aid

    def test_is_frozen(self) -> None:
        event = RunStarted(
            run_id=RunId("phronesis.runtime.run.x"),
            agent_id=AgentId("phronesis.agents.x"),
        )

        with pytest.raises(AttributeError):
            event.run_id = RunId("phronesis.runtime.run.y")  # type: ignore[misc]


class TestTextDelta:
    def test_carries_text(self) -> None:
        event = TextDelta(text="hello")

        assert event.text == "hello"

    def test_equality_is_value_based(self) -> None:
        assert TextDelta(text="a") == TextDelta(text="a")
        assert TextDelta(text="a") != TextDelta(text="b")


class TestToolCallStarted:
    def test_default_args_is_empty(self) -> None:
        event = ToolCallStarted(
            tool_call_id="c1",
            tool_id=ToolId("phronesis.tools.search"),
            tool_name="search",
        )

        assert dict(event.args) == {}

    def test_stored_args_are_immutable(self) -> None:
        payload = {"q": "phronesis"}

        event = ToolCallStarted(
            tool_call_id="c1",
            tool_id=ToolId("phronesis.tools.search"),
            tool_name="search",
            args=payload,
        )
        payload["q"] = "mutated"

        assert dict(event.args) == {"q": "phronesis"}
        assert isinstance(event.args, MappingProxyType)


class TestToolCallCompleted:
    def test_default_is_not_error(self) -> None:
        event = ToolCallCompleted(tool_call_id="c1", result={"ok": True})

        assert event.is_error is False

    def test_error_flag_round_trips(self) -> None:
        event = ToolCallCompleted(
            tool_call_id="c1",
            result={"error": "tool_timeout"},
            is_error=True,
        )

        assert event.is_error is True


class TestRunCompleted:
    def test_carries_result(self) -> None:
        result = _result()

        event = RunCompleted(result=result)

        assert event.result is result


class TestRunFailed:
    def test_carries_error(self) -> None:
        err = AgentMaxIterationsError("hit cap")

        event = RunFailed(error=err)

        assert event.error is err


class TestAgentEventUnion:
    @pytest.mark.parametrize(
        "event",
        [
            RunStarted(
                run_id=RunId("phronesis.runtime.run.x"),
                agent_id=AgentId("phronesis.agents.x"),
            ),
            TextDelta(text="hi"),
            ToolCallStarted(
                tool_call_id="c1",
                tool_id=ToolId("phronesis.tools.search"),
                tool_name="search",
            ),
            ToolCallCompleted(tool_call_id="c1", result=None),
            RunCompleted(result=_result()),
            RunFailed(error=AgentMaxIterationsError("hit cap")),
        ],
    )
    def test_every_event_is_an_agent_event(self, event: AgentEvent) -> None:
        assert isinstance(
            event,
            RunStarted | TextDelta | ToolCallStarted | ToolCallCompleted | RunCompleted | RunFailed,
        )
