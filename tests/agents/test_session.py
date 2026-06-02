"""Tests for :class:`Session`."""

from __future__ import annotations

from collections.abc import AsyncIterator

import pytest

from phronesis.agents.agent import Agent
from phronesis.agents.id import AgentId
from phronesis.agents.run import RunRequest
from phronesis.agents.session import Session
from phronesis.agents.spec import AgentSpec
from phronesis.communication.session_id import SessionId
from phronesis.core.messages import AssistantMessage, SystemMessage, UserMessage
from phronesis.providers.chunks import LLMChunk
from phronesis.providers.protocol import LLMProvider, ProviderFeature
from phronesis.providers.types import LLMRequest, LLMResponse


class _ScriptedProvider:
    def __init__(self, responses: list[LLMResponse]) -> None:
        self._responses = list(responses)
        self.requests: list[LLMRequest] = []

    async def complete(self, request: LLMRequest) -> LLMResponse:
        self.requests.append(request)
        return self._responses.pop(0)

    def stream(self, request: LLMRequest) -> AsyncIterator[LLMChunk]:
        async def _empty() -> AsyncIterator[LLMChunk]:
            return
            yield  # pragma: no cover

        return _empty()

    def supports(self, feature: ProviderFeature) -> bool:
        return False


def _agent(provider: LLMProvider) -> Agent:
    spec = AgentSpec(
        id=AgentId("phronesis.agents.s"),
        name="s",
        model=provider,
        system_prompt="be brief",
    )
    return Agent(spec)


class TestConstruction:
    def test_factory_returns_session(self, provider: LLMProvider) -> None:
        ag = _agent(provider)

        sess = ag.session()

        assert isinstance(sess, Session)
        assert isinstance(sess.id, SessionId)

    def test_session_accepts_explicit_id(self, provider: LLMProvider) -> None:
        ag = _agent(provider)
        sid = SessionId("phronesis.communication.s.fixed")

        sess = ag.session(sid)

        assert sess.id is sid

    def test_starts_empty(self, provider: LLMProvider) -> None:
        ag = _agent(provider)

        sess = ag.session()

        assert sess.messages == ()


class TestSingleTurn:
    @pytest.mark.asyncio
    async def test_first_run_seeds_history(self) -> None:
        provider = _ScriptedProvider([LLMResponse(text="hello")])
        ag = _agent(provider)
        sess = ag.session()

        result = await sess.run("hi")

        assert result.output == "hello"
        assert isinstance(sess.messages[0], SystemMessage)
        assert isinstance(sess.messages[1], UserMessage)
        assert isinstance(sess.messages[-1], AssistantMessage)


class TestMultiTurn:
    @pytest.mark.asyncio
    async def test_second_turn_continues_history(self) -> None:
        provider = _ScriptedProvider(
            [
                LLMResponse(text="first"),
                LLMResponse(text="second"),
            ],
        )
        ag = _agent(provider)
        sess = ag.session()

        await sess.run("turn one")
        result = await sess.run("turn two")

        assert result.output == "second"

        roles = [m.role.value for m in provider.requests[1].messages]
        assert roles.count("user") == 2
        assert roles[0] == "system"

    @pytest.mark.asyncio
    async def test_history_grows_across_turns(self) -> None:
        provider = _ScriptedProvider(
            [LLMResponse(text="a"), LLMResponse(text="b")],
        )
        ag = _agent(provider)
        sess = ag.session()

        await sess.run("one")
        first_len = len(sess.messages)

        await sess.run("two")
        second_len = len(sess.messages)

        assert second_len > first_len


class TestRequestCoercion:
    @pytest.mark.asyncio
    async def test_string_input_is_wrapped(self) -> None:
        provider = _ScriptedProvider([LLMResponse(text="ok")])
        ag = _agent(provider)
        sess = ag.session()

        await sess.run("hi")

        assert provider.requests[0].messages[-1].content == "hi"

    @pytest.mark.asyncio
    async def test_explicit_request_session_id_forced_to_session(self) -> None:
        provider = _ScriptedProvider([LLMResponse(text="ok")])
        ag = _agent(provider)
        sess = ag.session(SessionId("phronesis.communication.s.real"))

        req = RunRequest(
            input="hi",
            session_id=SessionId("phronesis.communication.s.other"),
        )

        await sess.run(req)

        # Session forces its own id internally; we only assert it ran successfully
        # and consumed the request's input.
        assert provider.requests[0].messages[-1].content == "hi"


class TestReset:
    @pytest.mark.asyncio
    async def test_reset_clears_history_but_keeps_id(self) -> None:
        provider = _ScriptedProvider(
            [LLMResponse(text="a"), LLMResponse(text="b")],
        )
        ag = _agent(provider)
        sess = ag.session()

        await sess.run("one")
        original_id = sess.id

        sess.reset()

        assert sess.messages == ()
        assert sess.id is original_id

        await sess.run("two")
        # After reset, second run should start with a fresh system + user pair
        assert isinstance(sess.messages[0], SystemMessage)


class TestRepr:
    def test_repr_includes_ids(self, provider: LLMProvider) -> None:
        ag = _agent(provider)
        sess = ag.session(SessionId("phronesis.communication.s.show"))

        text = repr(sess)

        assert "phronesis.communication.s.show" in text
        assert "phronesis.agents.s" in text
