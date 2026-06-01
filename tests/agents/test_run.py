"""Tests for ``RunId``, ``RunRequest`` and ``Result``."""

from __future__ import annotations

from types import MappingProxyType

import pytest

from phronesis._internal.ids.id import Id
from phronesis.agents.errors import AgentMaxIterationsError
from phronesis.agents.run import (
    Result,
    RunId,
    RunRequest,
    TokenUsage,
    run_id_generator,
)
from phronesis.communication.session_id import SessionId
from phronesis.core.messages import (
    AssistantMessage,
    TextBlock,
    ToolUseBlock,
    UserMessage,
)


class TestRunId:
    def test_prefix_is_rid(self) -> None:
        assert RunId.prefix == "RID"

    def test_is_subclass_of_id(self) -> None:
        assert issubclass(RunId, Id)

    def test_short_has_rid_prefix(self) -> None:
        rid = RunId("phronesis.runtime.run.alpha")

        assert rid.short.startswith("RID-")
        assert len(rid.short) == len("RID-") + 8

    def test_is_frozen(self) -> None:
        rid = RunId("phronesis.runtime.run.alpha")

        with pytest.raises(AttributeError):
            rid.canonical = "other"  # type: ignore[misc]


class TestRunIdGenerator:
    def test_from_canonical_builds_run_id(self) -> None:
        rid = run_id_generator.from_canonical("phronesis.runtime.run.x")

        assert isinstance(rid, RunId)
        assert rid.canonical == "phronesis.runtime.run.x"

    def test_from_canonical_rejects_invalid(self) -> None:
        with pytest.raises(ValueError):
            run_id_generator.from_canonical("1.bad")


class TestRunRequestDefaults:
    def test_defaults_session_to_none(self) -> None:
        req = RunRequest(input="hi")

        assert req.session_id is None

    def test_defaults_max_iterations_to_none(self) -> None:
        req = RunRequest(input="hi")

        assert req.max_iterations is None

    def test_default_metadata_is_empty_mapping(self) -> None:
        req = RunRequest(input="hi")

        assert dict(req.metadata) == {}

    def test_input_is_required(self) -> None:
        with pytest.raises(TypeError):
            RunRequest()  # type: ignore[call-arg]


class TestRunRequestMetadata:
    def test_metadata_is_stored_immutably(self) -> None:
        payload = {"trace": "abc"}

        req = RunRequest(input="hi", metadata=payload)
        payload["trace"] = "mutated"

        assert dict(req.metadata) == {"trace": "abc"}
        assert isinstance(req.metadata, MappingProxyType)


class TestRunRequestFrozen:
    def test_is_frozen(self) -> None:
        req = RunRequest(input="hi")

        with pytest.raises(AttributeError):
            req.input = "other"  # type: ignore[misc]


class TestRunRequestSession:
    def test_session_id_is_round_tripped(self) -> None:
        sid = SessionId("phronesis.sessions.s1")

        req = RunRequest(input="hi", session_id=sid)

        assert req.session_id is sid


class TestResultDefaults:
    def _make(self, **overrides: object) -> Result:
        base: dict[str, object] = {
            "run_id": RunId("phronesis.runtime.run.x"),
            "output": "done",
            "tokens": TokenUsage(input_tokens=10, output_tokens=5),
            "iterations": 1,
            "tool_calls": (),
            "messages": (),
        }
        base.update(overrides)
        return Result(**base)  # type: ignore[arg-type]

    def test_defaults_success_true(self) -> None:
        result = self._make()

        assert result.success is True

    def test_defaults_error_none(self) -> None:
        result = self._make()

        assert result.error is None

    def test_defaults_cost_none(self) -> None:
        result = self._make()

        assert result.cost_usd is None


class TestResultPayload:
    def test_carries_token_usage(self) -> None:
        usage = TokenUsage(input_tokens=42, output_tokens=7)

        result = Result(
            run_id=RunId("phronesis.runtime.run.x"),
            output="ok",
            tokens=usage,
            iterations=2,
            tool_calls=(),
            messages=(),
        )

        assert result.tokens is usage

    def test_messages_round_trip(self) -> None:
        history = (
            UserMessage(content=(TextBlock(text="hi"),)),
            AssistantMessage(content=(TextBlock(text="hello"),)),
        )

        result = Result(
            run_id=RunId("phronesis.runtime.run.x"),
            output="hello",
            tokens=TokenUsage(),
            iterations=1,
            tool_calls=(),
            messages=history,
        )

        assert result.messages == history

    def test_tool_calls_round_trip(self) -> None:
        call = ToolUseBlock(tool_call_id="c1", tool_name="search", args={"q": "x"})

        result = Result(
            run_id=RunId("phronesis.runtime.run.x"),
            output="ok",
            tokens=TokenUsage(),
            iterations=1,
            tool_calls=(call,),
            messages=(),
        )

        assert result.tool_calls == (call,)


class TestResultFailure:
    def test_failure_records_error(self) -> None:
        err = AgentMaxIterationsError("hit cap")

        result = Result(
            run_id=RunId("phronesis.runtime.run.x"),
            output=None,
            tokens=TokenUsage(),
            iterations=10,
            tool_calls=(),
            messages=(),
            success=False,
            error=err,
        )

        assert result.success is False
        assert result.error is err


class TestResultFrozen:
    def test_is_frozen(self) -> None:
        result = Result(
            run_id=RunId("phronesis.runtime.run.x"),
            output="ok",
            tokens=TokenUsage(),
            iterations=1,
            tool_calls=(),
            messages=(),
        )

        with pytest.raises(AttributeError):
            result.success = False  # type: ignore[misc]


class TestResultRepr:
    def test_includes_run_id_and_success(self) -> None:
        result = Result(
            run_id=RunId("phronesis.runtime.run.x"),
            output="ok",
            tokens=TokenUsage(input_tokens=5, output_tokens=7),
            iterations=3,
            tool_calls=(),
            messages=(),
        )

        text = repr(result)

        assert "phronesis.runtime.run.x" in text
        assert "success=True" in text

    def test_includes_counts(self) -> None:
        result = Result(
            run_id=RunId("phronesis.runtime.run.x"),
            output="ok",
            tokens=TokenUsage(input_tokens=10, output_tokens=20),
            iterations=4,
            tool_calls=(),
            messages=(),
        )

        text = repr(result)

        assert "iterations=4" in text
        assert "tokens=30" in text

    def test_does_not_include_output_body(self) -> None:
        result = Result(
            run_id=RunId("phronesis.runtime.run.x"),
            output="secret payload",
            tokens=TokenUsage(),
            iterations=1,
            tool_calls=(),
            messages=(),
        )

        text = repr(result)

        assert "secret payload" not in text
