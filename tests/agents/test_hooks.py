"""Tests for :class:`AgentHooks` integration in the loop."""

from __future__ import annotations

from collections.abc import AsyncIterator, Sequence

import pytest

from phronesis.agents.agent import Agent
from phronesis.agents.hooks import AgentHooks
from phronesis.agents.id import AgentId
from phronesis.agents.spec import AgentSpec
from phronesis.core.messages import ToolResultBlock, ToolUseBlock
from phronesis.providers.chunks import LLMChunk
from phronesis.providers.protocol import ProviderFeature
from phronesis.providers.types import LLMRequest, LLMResponse, ToolCall


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

    async def count_tokens_exact(self, messages: Sequence[object]) -> int | None:
        return None


def _spec(provider: object, *, hooks: AgentHooks | None = None) -> AgentSpec:
    kwargs: dict[str, object] = {}

    if hooks is not None:
        kwargs["hooks"] = hooks

    return AgentSpec(
        id=AgentId("phronesis.agents.x"),
        name="x",
        model=provider,  # type: ignore[arg-type]
        system_prompt="hi",
        **kwargs,  # type: ignore[arg-type]
    )


class TestOnIteration:
    @pytest.mark.asyncio
    async def test_called_once_per_iteration(self) -> None:
        provider = _StubProvider([LLMResponse(text="done", finish_reason="stop")])
        seen: list[int] = []
        hooks = AgentHooks(on_iteration=lambda i: seen.append(i))
        agent = Agent(_spec(provider, hooks=hooks))

        await agent.run("hi")

        assert seen == [1]

    @pytest.mark.asyncio
    async def test_async_hook_is_awaited(self) -> None:
        provider = _StubProvider([LLMResponse(text="done", finish_reason="stop")])
        seen: list[int] = []

        async def hook(i: int) -> None:
            seen.append(i)

        agent = Agent(_spec(provider, hooks=AgentHooks(on_iteration=hook)))

        await agent.run("hi")

        assert seen == [1]


class TestOnToolCall:
    @pytest.mark.asyncio
    async def test_called_for_each_tool_call(self) -> None:
        provider = _StubProvider(
            [
                LLMResponse(
                    finish_reason="tool_use",
                    tool_calls=(ToolCall(call_id="t1", tool_name="ghost", arguments={}),),
                ),
                LLMResponse(text="done", finish_reason="stop"),
            ],
        )
        seen: list[tuple[ToolUseBlock, ToolResultBlock]] = []
        hooks = AgentHooks(on_tool_call=lambda use, res: seen.append((use, res)))
        agent = Agent(_spec(provider, hooks=hooks))

        await agent.run("hi")

        assert len(seen) == 1
        use, res = seen[0]
        assert use.tool_name == "ghost"
        assert res.is_error is True


class TestOnRunComplete:
    @pytest.mark.asyncio
    async def test_called_on_success(self) -> None:
        provider = _StubProvider([LLMResponse(text="done", finish_reason="stop")])
        seen: list[object] = []
        hooks = AgentHooks(on_run_complete=lambda r: seen.append(r))
        agent = Agent(_spec(provider, hooks=hooks))

        result = await agent.run("hi")

        assert len(seen) == 1
        assert seen[0] is result


class TestHookFailureIsSwallowed:
    @pytest.mark.asyncio
    async def test_iteration_hook_exception_does_not_abort_run(self) -> None:
        provider = _StubProvider([LLMResponse(text="done", finish_reason="stop")])

        def boom(i: int) -> None:
            raise RuntimeError("boom")

        agent = Agent(_spec(provider, hooks=AgentHooks(on_iteration=boom)))

        result = await agent.run("hi")

        assert result.success is True


class TestWithHooksFluent:
    @pytest.mark.asyncio
    async def test_with_hooks_returns_new_agent(self) -> None:
        provider = _StubProvider([LLMResponse(text="done", finish_reason="stop")])
        agent = Agent(_spec(provider))
        seen: list[int] = []
        hooked = agent.with_hooks(AgentHooks(on_iteration=lambda i: seen.append(i)))

        assert hooked is not agent
        assert agent.spec.hooks.on_iteration is None
        assert hooked.spec.hooks.on_iteration is not None
