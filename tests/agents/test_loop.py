"""Tests for the agent tool-calling :func:`run_loop`."""

from __future__ import annotations

import asyncio
from collections.abc import AsyncIterator
from typing import Any

import pytest

from phronesis.agents.errors import AgentExecutionError, AgentMaxIterationsError
from phronesis.agents.id import AgentId
from phronesis.agents.loop import run_loop
from phronesis.agents.run import RunRequest
from phronesis.agents.spec import AgentSpec
from phronesis.core.messages import (
    AssistantMessage,
    SystemMessage,
    TextBlock,
    ToolMessage,
    ToolResultBlock,
    ToolUseBlock,
    UserMessage,
)
from phronesis.providers.chunks import LLMChunk
from phronesis.providers.protocol import LLMProvider, ProviderFeature
from phronesis.providers.types import LLMRequest, LLMResponse, ToolCall
from phronesis.providers.usage import TokenUsage
from phronesis.tools.decorator import tool
from phronesis.tools.errors import ToolError
from phronesis.tools.tool import Tool


class _ScriptedProvider:
    """Provider that returns a scripted sequence of :class:`LLMResponse`."""

    def __init__(self, responses: list[LLMResponse]) -> None:
        self._responses = list(responses)
        self.requests: list[LLMRequest] = []

    async def complete(self, request: LLMRequest) -> LLMResponse:
        self.requests.append(request)

        if not self._responses:
            raise AssertionError("scripted provider ran out of responses")

        return self._responses.pop(0)

    def stream(self, request: LLMRequest) -> AsyncIterator[LLMChunk]:
        async def _empty() -> AsyncIterator[LLMChunk]:
            return
            yield  # pragma: no cover

        return _empty()

    def supports(self, feature: ProviderFeature) -> bool:
        return False


class _ExplodingProvider:
    async def complete(self, request: LLMRequest) -> LLMResponse:
        raise RuntimeError("transport boom")

    def stream(self, request: LLMRequest) -> AsyncIterator[LLMChunk]:
        async def _empty() -> AsyncIterator[LLMChunk]:
            return
            yield  # pragma: no cover

        return _empty()

    def supports(self, feature: ProviderFeature) -> bool:
        return False


def _spec(
    provider: LLMProvider, *, tools: tuple[Tool, ...] = (), max_iterations: int = 5
) -> AgentSpec:
    return AgentSpec(
        id=AgentId("phronesis.agents.x"),
        name="x",
        model=provider,
        system_prompt="be brief",
        tools=tools,
        max_iterations=max_iterations,
    )


@tool(name="echo")
def _echo(value: str) -> dict[str, Any]:
    return {"value": value}


@tool(name="boom")
def _boom() -> dict[str, Any]:
    raise RuntimeError("kaboom")


@tool(name="reject")
def _reject() -> dict[str, Any]:
    raise ToolError("tool said no", details={"why": "policy"})


@tool(name="slow")
async def _slow(label: str) -> dict[str, Any]:
    await asyncio.sleep(0)
    return {"label": label}


class TestSimpleCompletion:
    @pytest.mark.asyncio
    async def test_returns_result_when_model_emits_no_tool_calls(self) -> None:
        provider = _ScriptedProvider(
            [LLMResponse(text="hello world", finish_reason="stop")],
        )
        spec = _spec(provider)

        result = await run_loop(spec, RunRequest(input="hi"))

        assert result.output == "hello world"
        assert result.iterations == 1
        assert result.tool_calls == ()
        assert result.success is True

    @pytest.mark.asyncio
    async def test_seeds_history_with_system_and_user(self) -> None:
        provider = _ScriptedProvider([LLMResponse(text="done")])
        spec = _spec(provider)

        result = await run_loop(spec, RunRequest(input="hi"))

        assert isinstance(result.messages[0], SystemMessage)
        assert isinstance(result.messages[1], UserMessage)
        assert isinstance(result.messages[-1], AssistantMessage)


class TestToolCalls:
    @pytest.mark.asyncio
    async def test_executes_single_tool_then_returns(self) -> None:
        provider = _ScriptedProvider(
            [
                LLMResponse(
                    text="",
                    tool_calls=(
                        ToolCall(call_id="c1", tool_name="echo", arguments={"value": "hi"}),
                    ),
                ),
                LLMResponse(text="final"),
            ],
        )
        spec = _spec(provider, tools=(_echo,))

        result = await run_loop(spec, RunRequest(input="go"))

        assert result.output == "final"
        assert result.iterations == 2
        assert len(result.tool_calls) == 1
        assert result.tool_calls[0].tool_name == "echo"

        tool_msg = next(m for m in result.messages if isinstance(m, ToolMessage))
        block = tool_msg.content[0]
        assert isinstance(block, ToolResultBlock)
        assert block.output == {"value": "hi"}
        assert block.is_error is False

    @pytest.mark.asyncio
    async def test_executes_parallel_tool_calls(self) -> None:
        provider = _ScriptedProvider(
            [
                LLMResponse(
                    tool_calls=(
                        ToolCall(call_id="c1", tool_name="slow", arguments={"label": "a"}),
                        ToolCall(call_id="c2", tool_name="slow", arguments={"label": "b"}),
                    ),
                ),
                LLMResponse(text="done"),
            ],
        )
        spec = _spec(provider, tools=(_slow,))

        result = await run_loop(spec, RunRequest(input="go"))

        tool_msg = next(m for m in result.messages if isinstance(m, ToolMessage))
        outputs = [b.output for b in tool_msg.content if isinstance(b, ToolResultBlock)]

        assert outputs == [{"label": "a"}, {"label": "b"}]

    @pytest.mark.asyncio
    async def test_tool_error_serialized_back_to_model(self) -> None:
        provider = _ScriptedProvider(
            [
                LLMResponse(
                    tool_calls=(ToolCall(call_id="c1", tool_name="reject", arguments={}),),
                ),
                LLMResponse(text="recovered"),
            ],
        )
        spec = _spec(provider, tools=(_reject,))

        result = await run_loop(spec, RunRequest(input="go"))

        tool_msg = next(m for m in result.messages if isinstance(m, ToolMessage))
        block = tool_msg.content[0]

        assert isinstance(block, ToolResultBlock)
        assert block.is_error is True
        assert isinstance(block.output, dict)
        assert result.output == "recovered"

    @pytest.mark.asyncio
    async def test_unbound_tool_serialized_as_tool_error(self) -> None:
        provider = _ScriptedProvider(
            [
                LLMResponse(
                    tool_calls=(ToolCall(call_id="c1", tool_name="ghost", arguments={}),),
                ),
                LLMResponse(text="ok"),
            ],
        )
        spec = _spec(provider, tools=(_echo,))

        result = await run_loop(spec, RunRequest(input="go"))

        tool_msg = next(m for m in result.messages if isinstance(m, ToolMessage))
        block = tool_msg.content[0]

        assert isinstance(block, ToolResultBlock)
        assert block.is_error is True

    @pytest.mark.asyncio
    async def test_non_tool_exception_aborts_with_agent_execution_error(self) -> None:
        provider = _ScriptedProvider(
            [
                LLMResponse(
                    tool_calls=(ToolCall(call_id="c1", tool_name="boom", arguments={}),),
                ),
            ],
        )
        spec = _spec(provider, tools=(_boom,))

        with pytest.raises(AgentExecutionError) as info:
            await run_loop(spec, RunRequest(input="go"))

        assert info.value.details["tool_name"] == "boom"


class TestProviderErrors:
    @pytest.mark.asyncio
    async def test_provider_failure_wraps_in_agent_execution_error(self) -> None:
        spec = _spec(_ExplodingProvider())

        with pytest.raises(AgentExecutionError) as info:
            await run_loop(spec, RunRequest(input="hi"))

        assert info.value.details["agent_id"] == "phronesis.agents.x"


class TestMaxIterations:
    @pytest.mark.asyncio
    async def test_runs_forever_capped_by_max_iterations(self) -> None:
        provider = _ScriptedProvider(
            [
                LLMResponse(
                    tool_calls=(
                        ToolCall(call_id=f"c{i}", tool_name="echo", arguments={"value": "x"}),
                    ),
                )
                for i in range(10)
            ],
        )
        spec = _spec(provider, tools=(_echo,), max_iterations=3)

        with pytest.raises(AgentMaxIterationsError) as info:
            await run_loop(spec, RunRequest(input="go"))

        assert info.value.details["max_iterations"] == 3

    @pytest.mark.asyncio
    async def test_request_max_iterations_overrides_spec(self) -> None:
        provider = _ScriptedProvider(
            [
                LLMResponse(
                    tool_calls=(
                        ToolCall(call_id=f"c{i}", tool_name="echo", arguments={"value": "x"}),
                    ),
                )
                for i in range(5)
            ],
        )
        spec = _spec(provider, tools=(_echo,), max_iterations=20)

        with pytest.raises(AgentMaxIterationsError) as info:
            await run_loop(spec, RunRequest(input="go", max_iterations=2))

        assert info.value.details["max_iterations"] == 2


class TestUsageAggregation:
    @pytest.mark.asyncio
    async def test_token_usage_is_summed_across_calls(self) -> None:
        provider = _ScriptedProvider(
            [
                LLMResponse(
                    tool_calls=(
                        ToolCall(call_id="c1", tool_name="echo", arguments={"value": "x"}),
                    ),
                    usage=TokenUsage(input_tokens=10, output_tokens=2),
                ),
                LLMResponse(
                    text="done",
                    usage=TokenUsage(input_tokens=5, output_tokens=3),
                ),
            ],
        )
        spec = _spec(provider, tools=(_echo,))

        result = await run_loop(spec, RunRequest(input="go"))

        assert result.tokens.input_tokens == 15
        assert result.tokens.output_tokens == 5

    @pytest.mark.asyncio
    async def test_token_usage_handles_missing_usage(self) -> None:
        provider = _ScriptedProvider([LLMResponse(text="done", usage=None)])
        spec = _spec(provider)

        result = await run_loop(spec, RunRequest(input="go"))

        assert result.tokens.input_tokens is None


class TestHistoryTranslation:
    @pytest.mark.asyncio
    async def test_provider_sees_translated_history_on_second_turn(self) -> None:
        provider = _ScriptedProvider(
            [
                LLMResponse(
                    tool_calls=(
                        ToolCall(call_id="c1", tool_name="echo", arguments={"value": "x"}),
                    ),
                ),
                LLMResponse(text="done"),
            ],
        )
        spec = _spec(provider, tools=(_echo,))

        await run_loop(spec, RunRequest(input="go"))

        second = provider.requests[1]
        roles = [m.role.value for m in second.messages]

        assert roles == ["system", "user", "assistant", "tool"]

        assistant = second.messages[2]
        assert assistant.tool_calls[0].call_id == "c1"

        tool_message = second.messages[3]
        assert tool_message.tool_call_id == "c1"
        assert tool_message.tool_output == {"value": "x"}


class TestResultShape:
    @pytest.mark.asyncio
    async def test_result_messages_close_with_assistant(self) -> None:
        provider = _ScriptedProvider([LLMResponse(text="bye")])
        spec = _spec(provider)

        result = await run_loop(spec, RunRequest(input="hi"))

        final = result.messages[-1]
        assert isinstance(final, AssistantMessage)
        text_block = final.content[0]
        assert isinstance(text_block, TextBlock)
        assert text_block.text == "bye"

    @pytest.mark.asyncio
    async def test_tool_use_block_is_recorded_in_result(self) -> None:
        provider = _ScriptedProvider(
            [
                LLMResponse(
                    tool_calls=(
                        ToolCall(call_id="c1", tool_name="echo", arguments={"value": "z"}),
                    ),
                ),
                LLMResponse(text="ok"),
            ],
        )
        spec = _spec(provider, tools=(_echo,))

        result = await run_loop(spec, RunRequest(input="go"))

        assert len(result.tool_calls) == 1
        recorded = result.tool_calls[0]
        assert isinstance(recorded, ToolUseBlock)
        assert recorded.tool_call_id == "c1"
        assert dict(recorded.args) == {"value": "z"}
