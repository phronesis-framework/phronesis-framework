"""Tests for budget enforcement in the agent loop."""

from __future__ import annotations

import asyncio
from collections.abc import AsyncIterator, Sequence

import pytest

from phronesis.agents.agent import Agent
from phronesis.agents.errors import AgentBudgetExceededError, AgentTimeoutError
from phronesis.agents.id import AgentId
from phronesis.agents.run import RunRequest
from phronesis.agents.spec import AgentSpec
from phronesis.core.messages import Message
from phronesis.providers.chunks import LLMChunk
from phronesis.providers.pricing import Pricing
from phronesis.providers.protocol import ProviderFeature
from phronesis.providers.types import LLMRequest, LLMResponse
from phronesis.providers.usage import TokenUsage


class _UsageProvider:
    """Provider that returns a configurable token usage on every call."""

    def __init__(self, input_tokens: int, output_tokens: int) -> None:
        self._response = LLMResponse(
            text="done",
            finish_reason="stop",
            usage=TokenUsage(input_tokens=input_tokens, output_tokens=output_tokens),
        )

    async def complete(self, request: LLMRequest) -> LLMResponse:
        return self._response

    def stream(self, request: LLMRequest) -> AsyncIterator[LLMChunk]:
        async def _empty() -> AsyncIterator[LLMChunk]:
            return
            yield  # pragma: no cover

        return _empty()

    def supports(self, feature: ProviderFeature) -> bool:
        return False

    def context_window_size(self) -> int:
        return 200_000

    def count_tokens(self, messages: Sequence[Message]) -> int:
        return 0

    async def count_tokens_exact(self, messages: Sequence[Message]) -> int | None:
        return None


class _SlowProvider:
    """Provider whose ``complete`` sleeps before returning."""

    def __init__(self, delay: float) -> None:
        self._delay = delay

    async def complete(self, request: LLMRequest) -> LLMResponse:
        await asyncio.sleep(self._delay)

        return LLMResponse(text="done", finish_reason="stop")

    def stream(self, request: LLMRequest) -> AsyncIterator[LLMChunk]:
        async def _empty() -> AsyncIterator[LLMChunk]:
            return
            yield  # pragma: no cover

        return _empty()

    def supports(self, feature: ProviderFeature) -> bool:
        return False

    def context_window_size(self) -> int:
        return 200_000

    def count_tokens(self, messages: Sequence[Message]) -> int:
        return 0

    async def count_tokens_exact(self, messages: Sequence[Message]) -> int | None:
        return None


def _spec(provider: object) -> AgentSpec:
    return AgentSpec(
        id=AgentId("phronesis.agents.x"),
        name="x",
        model=provider,  # type: ignore[arg-type]
        system_prompt="hi",
    )


class TestMaxTokens:
    @pytest.mark.asyncio
    async def test_does_not_raise_below_threshold(self) -> None:
        provider = _UsageProvider(input_tokens=10, output_tokens=5)
        agent = Agent(_spec(provider))

        result = await agent.run(RunRequest(input="hi", max_tokens=100))

        assert result.success is True

    @pytest.mark.asyncio
    async def test_raises_when_exceeded(self) -> None:
        provider = _UsageProvider(input_tokens=80, output_tokens=80)
        agent = Agent(_spec(provider))

        with pytest.raises(AgentBudgetExceededError) as ei:
            await agent.run(RunRequest(input="hi", max_tokens=100))

        assert ei.value.details["limit"] == "max_tokens"
        assert ei.value.details["threshold"] == 100
        assert ei.value.details["observed"] == 160

    @pytest.mark.asyncio
    async def test_unset_means_unlimited(self) -> None:
        provider = _UsageProvider(input_tokens=10_000, output_tokens=10_000)
        agent = Agent(_spec(provider))

        result = await agent.run(RunRequest(input="hi"))

        assert result.success is True


class TestTimeout:
    @pytest.mark.asyncio
    async def test_does_not_raise_when_fast(self) -> None:
        provider = _SlowProvider(delay=0.0)
        agent = Agent(_spec(provider))

        result = await agent.run(RunRequest(input="hi", timeout_seconds=1.0))

        assert result.success is True

    @pytest.mark.asyncio
    async def test_raises_when_slow(self) -> None:
        provider = _SlowProvider(delay=0.2)
        agent = Agent(_spec(provider))

        with pytest.raises(AgentTimeoutError) as ei:
            await agent.run(RunRequest(input="hi", timeout_seconds=0.05))

        assert ei.value.details["limit"] == "timeout_seconds"
        assert ei.value.details["threshold"] == 0.05

    @pytest.mark.asyncio
    async def test_timeout_error_is_budget_error(self) -> None:
        provider = _SlowProvider(delay=0.2)
        agent = Agent(_spec(provider))

        with pytest.raises(AgentBudgetExceededError):
            await agent.run(RunRequest(input="hi", timeout_seconds=0.05))


def _priced_spec(provider: object, pricing: Pricing) -> AgentSpec:
    return AgentSpec(
        id=AgentId("phronesis.agents.priced"),
        name="priced",
        model=provider,  # type: ignore[arg-type]
        system_prompt="hi",
        pricing=pricing,
    )


class TestMaxCostUsd:
    @pytest.mark.asyncio
    async def test_result_carries_no_cost_without_pricing(self) -> None:
        agent = Agent(_spec(_UsageProvider(input_tokens=1_000, output_tokens=1_000)))

        result = await agent.run("hi")

        assert result.cost_usd is None

    @pytest.mark.asyncio
    async def test_result_carries_cost_when_priced(self) -> None:
        provider = _UsageProvider(input_tokens=1_000_000, output_tokens=500_000)
        pricing = Pricing(input=3.0, output=15.0)
        agent = Agent(_priced_spec(provider, pricing))

        result = await agent.run("hi")

        assert result.cost_usd == pytest.approx(10.5)

    @pytest.mark.asyncio
    async def test_does_not_raise_below_threshold(self) -> None:
        provider = _UsageProvider(input_tokens=1_000, output_tokens=0)
        agent = Agent(_priced_spec(provider, Pricing(input=3.0)))

        result = await agent.run(RunRequest(input="hi", max_cost_usd=1.0))

        assert result.output == "done"

    @pytest.mark.asyncio
    async def test_raises_when_exceeded(self) -> None:
        provider = _UsageProvider(input_tokens=1_000_000, output_tokens=0)
        agent = Agent(_priced_spec(provider, Pricing(input=3.0)))

        with pytest.raises(AgentBudgetExceededError) as exc_info:
            await agent.run(RunRequest(input="hi", max_cost_usd=1.0))

        assert exc_info.value.details["limit"] == "max_cost_usd"
        assert exc_info.value.details["observed"] == pytest.approx(3.0)

    @pytest.mark.asyncio
    async def test_cap_is_inert_without_pricing(self) -> None:
        provider = _UsageProvider(input_tokens=1_000_000, output_tokens=1_000_000)
        agent = Agent(_spec(provider))

        result = await agent.run(RunRequest(input="hi", max_cost_usd=0.000_001))

        assert result.output == "done"
