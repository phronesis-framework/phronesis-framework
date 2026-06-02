"""Tests for :class:`Context` injection in the agent loop."""

from __future__ import annotations

from collections.abc import AsyncIterator
from typing import Any

import pytest

from phronesis.agents.id import AgentId
from phronesis.agents.loop import run_loop
from phronesis.agents.run import RunRequest
from phronesis.agents.spec import AgentSpec
from phronesis.communication.session_id import SessionId
from phronesis.context.context import Context
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


_received: dict[str, Context | None] = {}


@tool(name="capture")
def _capture(ctx: Context, marker: str) -> dict[str, Any]:
    _received[marker] = ctx
    return {"ok": True}


def _spec(provider: LLMProvider, *, tools: tuple[Tool, ...]) -> AgentSpec:
    return AgentSpec(
        id=AgentId("phronesis.agents.ctx"),
        name="ctx",
        model=provider,
        system_prompt="hi",
        tools=tools,
    )


class TestContextInjection:
    @pytest.mark.asyncio
    async def test_tool_sees_agent_and_run_ids(self) -> None:
        _received.clear()
        provider = _ScriptedProvider(
            [
                LLMResponse(
                    tool_calls=(
                        ToolCall(
                            call_id="c1",
                            tool_name="capture",
                            arguments={"marker": "a"},
                        ),
                    ),
                ),
                LLMResponse(text="done"),
            ],
        )
        spec = _spec(provider, tools=(_capture,))

        result = await run_loop(spec, RunRequest(input="go"))

        ctx = _received["a"]
        assert ctx is not None
        assert ctx.agent_id is spec.id
        assert ctx.run_id is result.run_id

    @pytest.mark.asyncio
    async def test_session_id_propagates_to_context(self) -> None:
        _received.clear()
        sid = SessionId("phronesis.communication.s.linked")
        provider = _ScriptedProvider(
            [
                LLMResponse(
                    tool_calls=(
                        ToolCall(
                            call_id="c1",
                            tool_name="capture",
                            arguments={"marker": "s"},
                        ),
                    ),
                ),
                LLMResponse(text="done"),
            ],
        )
        spec = _spec(provider, tools=(_capture,))

        await run_loop(spec, RunRequest(input="go", session_id=sid))

        ctx = _received["s"]
        assert ctx is not None
        assert ctx.session_id is sid

    @pytest.mark.asyncio
    async def test_request_metadata_is_visible_to_tool(self) -> None:
        _received.clear()
        provider = _ScriptedProvider(
            [
                LLMResponse(
                    tool_calls=(
                        ToolCall(
                            call_id="c1",
                            tool_name="capture",
                            arguments={"marker": "m"},
                        ),
                    ),
                ),
                LLMResponse(text="done"),
            ],
        )
        spec = _spec(provider, tools=(_capture,))

        await run_loop(
            spec,
            RunRequest(input="go", metadata={"trace_hint": "x"}),
        )

        ctx = _received["m"]
        assert ctx is not None
        assert dict(ctx.metadata) == {"trace_hint": "x"}
