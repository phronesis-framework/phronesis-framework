"""Tests for :func:`phronesis.memory.make_memory_tools`."""

from __future__ import annotations

import pytest

from phronesis.memory.kv import InMemoryKeyValueStore
from phronesis.memory.scope import MemoryLevel, MemoryScope
from phronesis.memory.tools import make_memory_tools
from phronesis.memory.vector import InMemoryVectorStore, VectorItem
from phronesis.memory.working import InMemoryWorkingStore
from tests.memory.conftest import FakeEmbeddingProvider


class TestFactory:
    def test_returns_no_tools_when_nothing_supplied(self) -> None:
        assert make_memory_tools() == ()

    def test_vector_without_embedding_raises(self) -> None:
        with pytest.raises(ValueError):
            make_memory_tools(vector=InMemoryVectorStore())

    def test_kv_only_produces_three_tools(self) -> None:
        tools = make_memory_tools(kv=InMemoryKeyValueStore())

        names = tuple(t.spec.name for t in tools)

        assert names == ("memory_remember", "memory_recall", "memory_forget")

    def test_full_kit_produces_five_tools(self) -> None:
        tools = make_memory_tools(
            working=InMemoryWorkingStore(),
            kv=InMemoryKeyValueStore(),
            vector=InMemoryVectorStore(),
            embedding=FakeEmbeddingProvider({}, 2),
        )

        assert len(tools) == 5


class TestRememberRecallForget:
    @pytest.mark.asyncio
    async def test_remember_recall_roundtrip(self) -> None:
        kv = InMemoryKeyValueStore()
        tools = make_memory_tools(kv=kv)
        by_name = {str(t.spec.name): t for t in tools}

        remember = by_name["memory_remember"]
        recall = by_name["memory_recall"]

        await remember(key="user.name", value="alice")
        result = await recall(key="user.name")

        assert result["value"] == "alice"

    @pytest.mark.asyncio
    async def test_forget_reports_deletion(self) -> None:
        kv = InMemoryKeyValueStore()
        tools = make_memory_tools(kv=kv)
        by_name = {str(t.spec.name): t for t in tools}

        await by_name["memory_remember"](key="k", value="v")

        result = await by_name["memory_forget"](key="k")

        assert result["deleted"] is True

    @pytest.mark.asyncio
    async def test_scope_resolver_is_honored(self) -> None:
        kv = InMemoryKeyValueStore()
        target = MemoryScope.agent("AID_x")
        tools = make_memory_tools(kv=kv, scope_resolver=lambda _: target)
        by_name = {str(t.spec.name): t for t in tools}

        await by_name["memory_remember"](key="k", value="v")

        assert await kv.get(target, "k") == "v"


class TestSearch:
    @pytest.mark.asyncio
    async def test_search_returns_results(self) -> None:
        vector = InMemoryVectorStore()
        scope = MemoryScope.session("_default")

        await vector.upsert(
            scope,
            (VectorItem(id="doc", text="hello", embedding=(1.0, 0.0), metadata={}),),
        )

        tools = make_memory_tools(
            vector=vector,
            embedding=FakeEmbeddingProvider({"hello": (1.0, 0.0)}, 2),
        )
        search = next(t for t in tools if t.spec.name == "memory_search")

        result = await search(query="hello")

        assert result["results"][0]["id"] == "doc"


class TestNote:
    @pytest.mark.asyncio
    async def test_note_appends_to_working_memory(self) -> None:
        working = InMemoryWorkingStore()
        tools = make_memory_tools(working=working)
        note = next(t for t in tools if t.spec.name == "memory_note")

        await note(content="first", tags=("a",), scope_level="run")

        scope = MemoryScope(level=MemoryLevel.RUN, id="_default")
        stored = await working.get(scope, "notes")

        assert stored == [{"content": "first", "tags": ["a"]}]
