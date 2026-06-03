"""Tests for :class:`phronesis.memory.MemoryAwareContextBuilder`."""

from __future__ import annotations

import pytest

from phronesis.context.input import BuildInput
from phronesis.core.messages import (
    AssistantMessage,
    Message,
    SystemMessage,
    TextBlock,
    UserMessage,
)
from phronesis.memory.context_builder import MemoryAwareContextBuilder
from phronesis.memory.scope import MemoryScope
from phronesis.memory.vector import InMemoryVectorStore, VectorItem
from tests.memory.conftest import FakeEmbeddingProvider, FakeProvider


def _user(text: str) -> UserMessage:
    return UserMessage(content=(TextBlock(text=text),))


def _text(message: Message) -> str:
    return "".join(block.text for block in message.content if isinstance(block, TextBlock))


def _input(
    *,
    system: str = "system",
    history: tuple[Message, ...] = (),
    new_input: UserMessage | None = None,
) -> BuildInput:
    return BuildInput(
        system_prompt=system,
        history=history,
        new_input=new_input,
        provider=FakeProvider(),
    )


class TestValidation:
    def test_top_k_must_be_positive(self, session_scope: MemoryScope) -> None:
        with pytest.raises(ValueError):
            MemoryAwareContextBuilder(
                vector_store=InMemoryVectorStore(),
                embedding_provider=FakeEmbeddingProvider({}, 2),
                scope=session_scope,
                top_k=0,
            )

    def test_max_chars_must_be_positive(self, session_scope: MemoryScope) -> None:
        with pytest.raises(ValueError):
            MemoryAwareContextBuilder(
                vector_store=InMemoryVectorStore(),
                embedding_provider=FakeEmbeddingProvider({}, 2),
                scope=session_scope,
                max_injected_chars=0,
            )


class TestBuild:
    @pytest.mark.asyncio
    async def test_injects_after_system_by_default(self, session_scope: MemoryScope) -> None:
        store = InMemoryVectorStore()

        await store.upsert(
            session_scope,
            (VectorItem(id="i1", text="relevant doc", embedding=(1.0, 0.0), metadata={}),),
        )

        builder = MemoryAwareContextBuilder(
            vector_store=store,
            embedding_provider=FakeEmbeddingProvider({"q": (1.0, 0.0)}, 2),
            scope=session_scope,
            min_score=0.0,
        )

        messages = await builder.build(_input(new_input=_user("q")))

        assert isinstance(messages[0], SystemMessage)
        assert "system" in _text(messages[0])
        assert isinstance(messages[1], SystemMessage)
        assert "relevant doc" in _text(messages[1])
        assert _text(messages[-1]) == "q"

    @pytest.mark.asyncio
    async def test_inject_before_system_position(self, session_scope: MemoryScope) -> None:
        store = InMemoryVectorStore()

        await store.upsert(
            session_scope,
            (VectorItem(id="i1", text="doc", embedding=(1.0,), metadata={}),),
        )

        builder = MemoryAwareContextBuilder(
            vector_store=store,
            embedding_provider=FakeEmbeddingProvider({"q": (1.0,)}, 1),
            scope=session_scope,
            min_score=0.0,
            injection_position="before_system",
        )

        messages = await builder.build(_input(new_input=_user("q")))

        assert isinstance(messages[0], SystemMessage)
        assert "doc" in _text(messages[0])
        assert "system" in _text(messages[1])

    @pytest.mark.asyncio
    async def test_no_query_skips_injection(self, session_scope: MemoryScope) -> None:
        store = InMemoryVectorStore()
        builder = MemoryAwareContextBuilder(
            vector_store=store,
            embedding_provider=FakeEmbeddingProvider({}, 2),
            scope=session_scope,
        )

        messages = await builder.build(_input(history=(), new_input=None))

        assert all("Relevant context" not in _text(m) for m in messages if m.content)

    @pytest.mark.asyncio
    async def test_query_falls_back_to_last_user_message(self, session_scope: MemoryScope) -> None:
        store = InMemoryVectorStore()

        await store.upsert(
            session_scope,
            (VectorItem(id="i1", text="found", embedding=(1.0,), metadata={}),),
        )

        builder = MemoryAwareContextBuilder(
            vector_store=store,
            embedding_provider=FakeEmbeddingProvider({"from history": (1.0,)}, 1),
            scope=session_scope,
            min_score=0.0,
        )

        history = (
            _user("from history"),
            AssistantMessage(content=(TextBlock(text="ack"),)),
        )

        messages = await builder.build(_input(history=history, new_input=None))

        assert any("found" in _text(m) for m in messages if isinstance(m, SystemMessage))

    @pytest.mark.asyncio
    async def test_max_chars_truncates_injection(self, session_scope: MemoryScope) -> None:
        store = InMemoryVectorStore()

        await store.upsert(
            session_scope,
            (
                VectorItem(
                    id="i1",
                    text="x" * 1000,
                    embedding=(1.0,),
                    metadata={},
                ),
            ),
        )

        builder = MemoryAwareContextBuilder(
            vector_store=store,
            embedding_provider=FakeEmbeddingProvider({"q": (1.0,)}, 1),
            scope=session_scope,
            min_score=0.0,
            max_injected_chars=50,
        )

        messages = await builder.build(_input(new_input=_user("q")))
        injected = next(m for m in messages if "Relevant context" in _text(m))

        assert len(_text(injected)) <= 50 + len("Relevant context retrieved from memory:\n\n")


class TestScopeResolver:
    @pytest.mark.asyncio
    async def test_callable_scope_is_resolved(self) -> None:
        store = InMemoryVectorStore()
        scope = MemoryScope.session("SID_dynamic")

        await store.upsert(
            scope,
            (VectorItem(id="i1", text="ok", embedding=(1.0,), metadata={}),),
        )

        builder = MemoryAwareContextBuilder(
            vector_store=store,
            embedding_provider=FakeEmbeddingProvider({"q": (1.0,)}, 1),
            scope=lambda _: scope,
            min_score=0.0,
        )

        messages = await builder.build(_input(new_input=_user("q")))

        assert any("ok" in _text(m) for m in messages if isinstance(m, SystemMessage))
