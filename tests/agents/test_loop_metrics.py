"""Tests for granular provider/tool/retry metric emission in the agent loop."""

from __future__ import annotations

from collections.abc import AsyncIterator
from typing import Any

import pytest

from phronesis.agents import loop as loop_module
from phronesis.agents.errors import AgentExecutionError
from phronesis.agents.id import AgentId
from phronesis.agents.loop import run_loop
from phronesis.agents.run import RunRequest
from phronesis.agents.spec import AgentSpec
from phronesis.obs import attributes as obs_attrs
from phronesis.providers.chunks import LLMChunk
from phronesis.providers.protocol import LLMProvider, ProviderFeature
from phronesis.providers.types import LLMRequest, LLMResponse, TokenUsage, ToolCall
from phronesis.tools.decorator import tool
from phronesis.tools.retry import RetryPolicy
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


class _FailingProvider:
    async def complete(self, request: LLMRequest) -> LLMResponse:
        raise RuntimeError("provider boom")

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


_FLAKY_CALLS = {"n": 0}


@tool(
    name="flaky",
    retry=RetryPolicy(max_attempts=3, retry_on=(RuntimeError,), backoff_seconds=0.0),
)
def _flaky() -> dict[str, Any]:
    _FLAKY_CALLS["n"] += 1

    if _FLAKY_CALLS["n"] < 2:
        raise RuntimeError("transient")

    return {"ok": True}


@tool(name="bad")
def _bad() -> dict[str, Any]:
    raise RuntimeError("nope")


def _spec(provider: LLMProvider, *, tools: tuple[Tool, ...] = ()) -> AgentSpec:
    return AgentSpec(
        id=AgentId("phronesis.agents.metrics"),
        name="metrics",
        model=provider,
        system_prompt="hi",
        tools=tools,
    )


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


_INSTRUMENT_NAMES = (
    "provider_requests",
    "provider_duration",
    "provider_tokens_input",
    "provider_tokens_output",
    "tool_invocations",
    "tool_duration",
    "tool_errors",
    "retry_attempts",
)


@pytest.fixture
def metric_recorder(monkeypatch: pytest.MonkeyPatch) -> list[_MetricRecord]:
    records: list[_MetricRecord] = []

    for name in _INSTRUMENT_NAMES:
        monkeypatch.setattr(
            loop_module.obs_metrics,
            name,
            _FakeInstrument(name, records),
        )

    return records


class TestProviderMetrics:
    @pytest.mark.asyncio
    async def test_provider_requests_counter_emitted_with_success_attr(
        self, metric_recorder: list[_MetricRecord]
    ) -> None:
        provider = _ScriptedProvider([LLMResponse(text="done")])
        spec = _spec(provider)

        await run_loop(spec, RunRequest(input="go"))

        adds = [r for r in metric_recorder if r.name == "provider_requests"]

        assert len(adds) == 1
        assert adds[0].attributes[obs_attrs.OPERATION_SUCCESS] is True
        assert adds[0].attributes[obs_attrs.PROVIDER_NAME] == "_ScriptedProvider"

    @pytest.mark.asyncio
    async def test_provider_duration_recorded(self, metric_recorder: list[_MetricRecord]) -> None:
        provider = _ScriptedProvider([LLMResponse(text="done")])
        spec = _spec(provider)

        await run_loop(spec, RunRequest(input="go"))

        durations = [r for r in metric_recorder if r.name == "provider_duration"]

        assert len(durations) == 1
        assert durations[0].value >= 0.0

    @pytest.mark.asyncio
    async def test_provider_token_counters_emitted_from_usage(
        self, metric_recorder: list[_MetricRecord]
    ) -> None:
        provider = _ScriptedProvider(
            [LLMResponse(text="done", usage=TokenUsage(input_tokens=10, output_tokens=5))],
        )
        spec = _spec(provider)

        await run_loop(spec, RunRequest(input="go"))

        ins = [r for r in metric_recorder if r.name == "provider_tokens_input"]
        outs = [r for r in metric_recorder if r.name == "provider_tokens_output"]

        assert len(ins) == 1
        assert ins[0].value == 10
        assert len(outs) == 1
        assert outs[0].value == 5

    @pytest.mark.asyncio
    async def test_provider_failure_records_success_false(
        self, metric_recorder: list[_MetricRecord]
    ) -> None:
        spec = _spec(_FailingProvider())

        with pytest.raises(AgentExecutionError):
            await run_loop(spec, RunRequest(input="go"))

        adds = [r for r in metric_recorder if r.name == "provider_requests"]

        assert len(adds) == 1
        assert adds[0].attributes[obs_attrs.OPERATION_SUCCESS] is False


class TestToolMetrics:
    @pytest.mark.asyncio
    async def test_tool_invocations_counter_on_success(
        self, metric_recorder: list[_MetricRecord]
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

        adds = [r for r in metric_recorder if r.name == "tool_invocations"]

        assert len(adds) == 1
        assert adds[0].attributes[obs_attrs.OPERATION_SUCCESS] is True
        assert adds[0].attributes[obs_attrs.TOOL_NAME] == "ping"

    @pytest.mark.asyncio
    async def test_tool_duration_recorded(self, metric_recorder: list[_MetricRecord]) -> None:
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

        durations = [r for r in metric_recorder if r.name == "tool_duration"]

        assert len(durations) == 1
        assert durations[0].value >= 0.0

    @pytest.mark.asyncio
    async def test_tool_errors_counter_on_failure(
        self, metric_recorder: list[_MetricRecord]
    ) -> None:
        provider = _ScriptedProvider(
            [
                LLMResponse(
                    tool_calls=(ToolCall(call_id="c1", tool_name="bad", arguments={}),),
                ),
                LLMResponse(text="done"),
            ],
        )
        spec = _spec(provider, tools=(_bad,))

        with pytest.raises(AgentExecutionError):
            await run_loop(spec, RunRequest(input="go"))

        errors = [r for r in metric_recorder if r.name == "tool_errors"]

        assert len(errors) == 1
        assert errors[0].attributes[obs_attrs.ERROR_TYPE] == "RuntimeError"


class TestRetryMetrics:
    @pytest.mark.asyncio
    async def test_retry_attempts_counter_emitted_on_each_retry(
        self, metric_recorder: list[_MetricRecord]
    ) -> None:
        _FLAKY_CALLS["n"] = 0

        provider = _ScriptedProvider(
            [
                LLMResponse(
                    tool_calls=(ToolCall(call_id="c1", tool_name="flaky", arguments={}),),
                ),
                LLMResponse(text="done"),
            ],
        )
        spec = _spec(provider, tools=(_flaky,))

        await run_loop(spec, RunRequest(input="go"))

        retries = [r for r in metric_recorder if r.name == "retry_attempts"]

        assert len(retries) == 1
        assert retries[0].attributes[obs_attrs.ERROR_TYPE] == "RuntimeError"
        assert retries[0].attributes[obs_attrs.TOOL_NAME] == "flaky"
