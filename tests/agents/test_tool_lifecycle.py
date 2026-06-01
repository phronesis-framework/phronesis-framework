"""Tests for tool ``setup``/``teardown`` lifecycle honoured by the loop."""

from __future__ import annotations

from collections.abc import AsyncIterator, Sequence

import pytest

from phronesis.agents.agent import Agent
from phronesis.agents.errors import AgentExecutionError
from phronesis.agents.id import AgentId
from phronesis.agents.spec import AgentSpec
from phronesis.providers.chunks import LLMChunk
from phronesis.providers.protocol import ProviderFeature
from phronesis.providers.types import LLMRequest, LLMResponse
from phronesis.tools.decorator import tool
from phronesis.tools.lifecycle import ToolLifecycle


class _StubProvider:
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

    def context_window_size(self) -> int:
        return 200_000

    def count_tokens(self, messages: Sequence[object]) -> int:
        return 0


def _make_agent(t: object) -> Agent:
    provider = _StubProvider([LLMResponse(text="done", finish_reason="stop")])
    spec = AgentSpec(
        id=AgentId("phronesis.agents.x"),
        name="x",
        model=provider,  # type: ignore[arg-type]
        system_prompt="hi",
        tools=(t,),  # type: ignore[arg-type]
    )

    return Agent(spec)


class TestSetupTeardown:
    @pytest.mark.asyncio
    async def test_setup_and_teardown_run_once(self) -> None:
        events: list[str] = []

        @tool(
            id="phronesis.tests.lc_basic",
            lifecycle=ToolLifecycle(
                setup=lambda: events.append("setup"),
                teardown=lambda: events.append("teardown"),
            ),
        )
        def t() -> str:
            return "x"

        await _make_agent(t).run("hi")

        assert events == ["setup", "teardown"]

    @pytest.mark.asyncio
    async def test_setup_runs_before_any_iteration(self) -> None:
        events: list[str] = []

        @tool(
            id="phronesis.tests.lc_order",
            lifecycle=ToolLifecycle(
                setup=lambda: events.append("setup"),
            ),
        )
        def t() -> str:
            events.append("call")

            return "x"

        provider = _StubProvider([LLMResponse(text="done", finish_reason="stop")])
        spec = AgentSpec(
            id=AgentId("phronesis.agents.x"),
            name="x",
            model=provider,  # type: ignore[arg-type]
            system_prompt="hi",
            tools=(t,),
        )
        await Agent(spec).run("hi")

        # Tool never invoked (no tool_use response), but setup still ran.
        assert events == ["setup"]

    @pytest.mark.asyncio
    async def test_async_callbacks_are_awaited(self) -> None:
        events: list[str] = []

        async def setup() -> None:
            events.append("setup")

        async def teardown() -> None:
            events.append("teardown")

        @tool(
            id="phronesis.tests.lc_async",
            lifecycle=ToolLifecycle(setup=setup, teardown=teardown),
        )
        def t() -> str:
            return "x"

        await _make_agent(t).run("hi")

        assert events == ["setup", "teardown"]

    @pytest.mark.asyncio
    async def test_teardown_runs_even_when_loop_raises(self) -> None:
        events: list[str] = []

        @tool(
            id="phronesis.tests.lc_teardown_on_error",
            lifecycle=ToolLifecycle(teardown=lambda: events.append("teardown")),
        )
        def t() -> str:
            return "x"

        # Provider that always loops -> AgentMaxIterationsError.
        provider = _StubProvider([])

        async def _always(req: LLMRequest) -> LLMResponse:
            raise RuntimeError("boom")

        provider.complete = _always  # type: ignore[method-assign]
        spec = AgentSpec(
            id=AgentId("phronesis.agents.x"),
            name="x",
            model=provider,  # type: ignore[arg-type]
            system_prompt="hi",
            tools=(t,),
        )
        agent = Agent(spec)

        with pytest.raises(AgentExecutionError):
            await agent.run("hi")

        assert events == ["teardown"]

    @pytest.mark.asyncio
    async def test_teardown_failure_is_swallowed(self) -> None:
        def boom() -> None:
            raise RuntimeError("teardown explodes")

        @tool(
            id="phronesis.tests.lc_teardown_boom",
            lifecycle=ToolLifecycle(teardown=boom),
        )
        def t() -> str:
            return "x"

        result = await _make_agent(t).run("hi")

        assert result.success is True
