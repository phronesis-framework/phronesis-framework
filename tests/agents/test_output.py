"""Tests for structured output: schema negotiation and answer coercion."""

from __future__ import annotations

from collections.abc import AsyncIterator, Sequence
from dataclasses import dataclass

import pytest
from pydantic import BaseModel

from phronesis.agents.agent import Agent
from phronesis.agents.errors import AgentOutputValidationError
from phronesis.agents.id import AgentId
from phronesis.agents.output import coerce_output, response_format_for
from phronesis.agents.spec import AgentSpec
from phronesis.core.messages import Message
from phronesis.providers.chunks import LLMChunk
from phronesis.providers.protocol import ProviderFeature
from phronesis.providers.types import LLMRequest, LLMResponse


class Verdict(BaseModel):
    route: str
    confidence: float


@dataclass
class Plain:
    label: str


class _Provider:
    """Provider recording the request, with configurable capabilities."""

    def __init__(self, text: str = "ok", *, structured: bool = True) -> None:
        self._text = text
        self._structured = structured
        self.requests: list[LLMRequest] = []

    async def complete(self, request: LLMRequest) -> LLMResponse:
        self.requests.append(request)

        return LLMResponse(text=self._text, finish_reason="stop")

    def stream(self, _request: LLMRequest) -> AsyncIterator[LLMChunk]:
        async def _empty() -> AsyncIterator[LLMChunk]:
            return
            yield  # pragma: no cover - empty async generator

        return _empty()

    def supports(self, feature: ProviderFeature) -> bool:
        return self._structured and feature is ProviderFeature.STRUCTURED_OUTPUT

    def context_window_size(self) -> int:
        return 200_000

    def count_tokens(self, _messages: Sequence[Message]) -> int:
        return 0

    async def count_tokens_exact(self, _messages: Sequence[Message]) -> int | None:
        return None


def _agent(provider: _Provider, output_type: type | None) -> Agent:
    return Agent(
        AgentSpec(
            id=AgentId("phronesis.agents.structured"),
            name="structured",
            model=provider,  # type: ignore[arg-type]
            system_prompt="answer",
            output_type=output_type,
        ),
    )


class TestResponseFormatFor:
    def test_no_output_type_means_no_format(self) -> None:
        assert response_format_for(None, _Provider()) is None  # type: ignore[arg-type]

    def test_provider_without_capability_gets_no_format(self) -> None:
        provider = _Provider(structured=False)

        assert response_format_for(Verdict, provider) is None  # type: ignore[arg-type]

    def test_schema_comes_from_the_declared_type(self) -> None:
        fmt = response_format_for(Verdict, _Provider())  # type: ignore[arg-type]

        assert fmt is not None
        assert fmt.name == "Verdict"
        assert set(fmt.schema["properties"]) == {"route", "confidence"}

    def test_strict_is_off_because_the_loop_validates_instead(self) -> None:
        fmt = response_format_for(Verdict, _Provider())  # type: ignore[arg-type]

        assert fmt is not None
        assert fmt.strict is False


class TestCoerceOutput:
    def test_no_type_returns_the_text(self) -> None:
        assert coerce_output(None, "plain", agent_id="a") == "plain"

    def test_str_type_returns_the_text(self) -> None:
        assert coerce_output(str, "plain", agent_id="a") == "plain"

    def test_pydantic_model_is_parsed(self) -> None:
        parsed = coerce_output(Verdict, '{"route":"bull","confidence":0.8}', agent_id="a")

        assert parsed == Verdict(route="bull", confidence=0.8)

    def test_dataclass_is_parsed(self) -> None:
        parsed = coerce_output(Plain, '{"label":"x"}', agent_id="a")

        assert parsed == Plain(label="x")

    def test_builtin_is_parsed(self) -> None:
        assert coerce_output(int, "42", agent_id="a") == 42

    def test_malformed_json_raises(self) -> None:
        with pytest.raises(AgentOutputValidationError):
            coerce_output(Verdict, "not json at all", agent_id="a")

    def test_schema_mismatch_raises_with_details(self) -> None:
        with pytest.raises(AgentOutputValidationError) as exc_info:
            coerce_output(Verdict, '{"route":"bull"}', agent_id="phronesis.agents.x")

        details = exc_info.value.details
        assert details["agent_id"] == "phronesis.agents.x"
        assert details["output_type"] == "Verdict"
        assert details["raw_output"] == '{"route":"bull"}'
        assert details["errors"]


class TestLoopIntegration:
    async def test_request_carries_the_schema(self) -> None:
        provider = _Provider('{"route":"bull","confidence":0.8}')

        await _agent(provider, Verdict).run("hi")

        assert provider.requests[0].response_format is not None

    async def test_request_omits_the_schema_without_capability(self) -> None:
        provider = _Provider('{"route":"bull","confidence":0.8}', structured=False)

        await _agent(provider, Verdict).run("hi")

        assert provider.requests[0].response_format is None

    async def test_result_output_is_an_instance_of_the_type(self) -> None:
        provider = _Provider('{"route":"bull","confidence":0.8}')

        result = await _agent(provider, Verdict).run("hi")

        assert isinstance(result.output, Verdict)
        assert result.output.route == "bull"

    async def test_validation_still_runs_without_provider_capability(self) -> None:
        provider = _Provider("sorry, no JSON here", structured=False)

        with pytest.raises(AgentOutputValidationError):
            await _agent(provider, Verdict).run("hi")

    async def test_free_form_agent_is_untouched(self) -> None:
        provider = _Provider("just words")

        result = await _agent(provider, None).run("hi")

        assert result.output == "just words"
        assert provider.requests[0].response_format is None

    async def test_stream_surfaces_validation_failure_as_run_failed(self) -> None:
        provider = _Provider("nope")
        events = [event async for event in _agent(provider, Verdict).stream("hi")]

        failure = events[-1]

        assert isinstance(getattr(failure, "error", None), AgentOutputValidationError)

    async def test_stream_yields_the_parsed_output(self) -> None:
        provider = _Provider('{"route":"bear","confidence":0.1}')
        events = [event async for event in _agent(provider, Verdict).stream("hi")]

        completed = events[-1]

        assert isinstance(completed.result.output, Verdict)  # type: ignore[union-attr]
