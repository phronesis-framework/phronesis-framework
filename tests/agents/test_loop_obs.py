"""Tests for observability instrumentation in the agent loop."""

from __future__ import annotations

from collections.abc import AsyncIterator
from contextlib import asynccontextmanager
from typing import Any

import pytest

from phronesis.agents import loop as loop_module
from phronesis.agents.errors import AgentMaxIterationsError
from phronesis.agents.id import AgentId
from phronesis.agents.loop import run_loop
from phronesis.agents.run import RunRequest
from phronesis.agents.spec import AgentSpec
from phronesis.communication.session_id import SessionId
from phronesis.obs import attributes as obs_attrs
from phronesis.providers.chunks import LLMChunk
from phronesis.providers.protocol import LLMProvider, ProviderFeature
from phronesis.providers.types import LLMRequest, LLMResponse, ToolCall
from phronesis.tools.decorator import tool
from phronesis.tools.tool import Tool


class _ScriptedProvider:
    def __init__(self, responses: list[LLMResponse]) -> None:
        self._responses = list(responses)

    async def complete(self, request: LLMRequest) -> LLMResponse:
        return self._responses.pop(0)

    def stream(self, request: LLMRequest) -> AsyncIterator[LLMChunk]:
        async def _empty() -> AsyncIterator[LLMChunk]:
            return
            yield  # pragma: no cover

        return _empty()

    def supports(self, feature: ProviderFeature) -> bool:
        return False


@tool(name="ping")
def _ping() -> dict[str, Any]:
    return {"ok": True}


def _spec(provider: LLMProvider, *, tools: tuple[Tool, ...] = ()) -> AgentSpec:
    return AgentSpec(
        id=AgentId("phronesis.agents.obs"),
        name="obs",
        model=provider,
        system_prompt="hi",
        tools=tools,
    )


class _SpanRecord:
    def __init__(self, name: str, attributes: dict[str, Any] | None) -> None:
        self.name = name
        self.attributes = dict(attributes or {})


class _MetricRecord:
    def __init__(self, kind: str, name: str, value: float, attributes: dict[str, Any]) -> None:
        self.kind = kind
        self.name = name
        self.value = value
        self.attributes = dict(attributes)


class _FakeInstrument:
    def __init__(self, name: str, sink: list[_MetricRecord]) -> None:
        self._name = name
        self._sink = sink

    def add(self, value: float, attributes: dict[str, Any] | None = None) -> None:
        self._sink.append(_MetricRecord("add", self._name, value, attributes or {}))

    def record(self, value: float, attributes: dict[str, Any] | None = None) -> None:
        self._sink.append(_MetricRecord("record", self._name, value, attributes or {}))


@pytest.fixture
def span_recorder(monkeypatch: pytest.MonkeyPatch) -> list[_SpanRecord]:
    spans: list[_SpanRecord] = []

    @asynccontextmanager
    async def _fake_span(
        name: str,
        *,
        attributes: dict[str, Any] | None = None,
    ) -> AsyncIterator[None]:
        spans.append(_SpanRecord(name, attributes))

        yield

    monkeypatch.setattr(loop_module, "start_span_async", _fake_span)

    return spans


@pytest.fixture
def metric_recorder(monkeypatch: pytest.MonkeyPatch) -> list[_MetricRecord]:
    records: list[_MetricRecord] = []

    monkeypatch.setattr(
        loop_module.obs_metrics, "agent_runs", _FakeInstrument("agent_runs", records)
    )
    monkeypatch.setattr(
        loop_module.obs_metrics,
        "agent_run_duration",
        _FakeInstrument("agent_run_duration", records),
    )
    monkeypatch.setattr(
        loop_module.obs_metrics,
        "agent_tool_calls_per_run",
        _FakeInstrument("agent_tool_calls_per_run", records),
    )

    return records


class TestSpans:
    @pytest.mark.asyncio
    async def test_emits_run_and_step_spans_for_simple_completion(
        self, span_recorder: list[_SpanRecord]
    ) -> None:
        provider = _ScriptedProvider([LLMResponse(text="done")])
        spec = _spec(provider)

        await run_loop(spec, RunRequest(input="go"))

        names = [s.name for s in span_recorder]

        assert names == ["phronesis.agents.run", "phronesis.agents.step"]

    @pytest.mark.asyncio
    async def test_run_span_carries_agent_and_run_attributes(
        self, span_recorder: list[_SpanRecord]
    ) -> None:
        provider = _ScriptedProvider([LLMResponse(text="done")])
        spec = _spec(provider)

        result = await run_loop(spec, RunRequest(input="go"))

        run_span = span_recorder[0]

        assert run_span.attributes[obs_attrs.AGENT_ID] == spec.id.canonical
        assert run_span.attributes[obs_attrs.AGENT_NAME] == spec.name
        assert run_span.attributes[obs_attrs.RUN_ID] == result.run_id.canonical

    @pytest.mark.asyncio
    async def test_session_id_attribute_only_when_provided(
        self, span_recorder: list[_SpanRecord]
    ) -> None:
        provider = _ScriptedProvider([LLMResponse(text="done")])
        spec = _spec(provider)

        await run_loop(spec, RunRequest(input="go"))

        run_span = span_recorder[0]

        assert obs_attrs.SESSION_ID not in run_span.attributes

    @pytest.mark.asyncio
    async def test_session_id_attribute_added_when_present(
        self, span_recorder: list[_SpanRecord]
    ) -> None:
        provider = _ScriptedProvider([LLMResponse(text="done")])
        spec = _spec(provider)
        sid = SessionId("phronesis.communication.s.fixed")

        await run_loop(spec, RunRequest(input="go", session_id=sid))

        run_span = span_recorder[0]

        assert run_span.attributes[obs_attrs.SESSION_ID] == sid.canonical

    @pytest.mark.asyncio
    async def test_step_span_includes_iteration_counter(
        self, span_recorder: list[_SpanRecord]
    ) -> None:
        provider = _ScriptedProvider([LLMResponse(text="done")])
        spec = _spec(provider)

        await run_loop(spec, RunRequest(input="go"))

        step_span = span_recorder[1]

        assert step_span.attributes["agent.step"] == 1

    @pytest.mark.asyncio
    async def test_tool_call_span_is_emitted_per_call(
        self, span_recorder: list[_SpanRecord]
    ) -> None:
        provider = _ScriptedProvider(
            [
                LLMResponse(
                    tool_calls=(ToolCall(call_id="c1", tool_name="ping", arguments={}),),
                ),
                LLMResponse(text="done"),
            ],
        )
        spec = _spec(provider, tools=(_ping,))

        await run_loop(spec, RunRequest(input="go"))

        tool_spans = [s for s in span_recorder if s.name == "phronesis.agents.tool_call"]

        assert len(tool_spans) == 1
        assert tool_spans[0].attributes[obs_attrs.TOOL_NAME] == "ping"
        assert tool_spans[0].attributes[obs_attrs.TOOL_CALL_ID] == "c1"


class TestMetrics:
    @pytest.mark.asyncio
    async def test_agent_runs_counter_incremented_once_per_run(
        self, metric_recorder: list[_MetricRecord]
    ) -> None:
        provider = _ScriptedProvider([LLMResponse(text="done")])
        spec = _spec(provider)

        await run_loop(spec, RunRequest(input="go"))

        adds = [r for r in metric_recorder if r.kind == "add" and r.name == "agent_runs"]

        assert len(adds) == 1
        assert adds[0].value == 1

    @pytest.mark.asyncio
    async def test_run_duration_recorded_on_success(
        self, metric_recorder: list[_MetricRecord]
    ) -> None:
        provider = _ScriptedProvider([LLMResponse(text="done")])
        spec = _spec(provider)

        await run_loop(spec, RunRequest(input="go"))

        durations = [
            r for r in metric_recorder if r.kind == "record" and r.name == "agent_run_duration"
        ]

        assert len(durations) == 1
        assert durations[0].value >= 0.0

    @pytest.mark.asyncio
    async def test_tool_calls_per_run_records_aggregate_count(
        self, metric_recorder: list[_MetricRecord]
    ) -> None:
        provider = _ScriptedProvider(
            [
                LLMResponse(
                    tool_calls=(
                        ToolCall(call_id="c1", tool_name="ping", arguments={}),
                        ToolCall(call_id="c2", tool_name="ping", arguments={}),
                    ),
                ),
                LLMResponse(text="done"),
            ],
        )
        spec = _spec(provider, tools=(_ping,))

        await run_loop(spec, RunRequest(input="go"))

        counts = [
            r
            for r in metric_recorder
            if r.kind == "record" and r.name == "agent_tool_calls_per_run"
        ]

        assert len(counts) == 1
        assert counts[0].value == 2

    @pytest.mark.asyncio
    async def test_metrics_recorded_even_when_run_raises(
        self, metric_recorder: list[_MetricRecord]
    ) -> None:
        provider = _ScriptedProvider(
            [
                LLMResponse(
                    tool_calls=(ToolCall(call_id="c1", tool_name="ping", arguments={}),),
                ),
                LLMResponse(
                    tool_calls=(ToolCall(call_id="c2", tool_name="ping", arguments={}),),
                ),
            ],
        )
        spec = _spec(provider, tools=(_ping,))

        with pytest.raises(AgentMaxIterationsError):
            await run_loop(spec, RunRequest(input="go", max_iterations=1))

        kinds = [(r.kind, r.name) for r in metric_recorder]

        assert ("add", "agent_runs") in kinds
        assert ("record", "agent_run_duration") in kinds
        assert ("record", "agent_tool_calls_per_run") in kinds
