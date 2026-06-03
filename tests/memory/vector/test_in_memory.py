"""Tests for :class:`phronesis.memory.InMemoryVectorStore`."""

from __future__ import annotations

import pytest

from phronesis.memory.scope import MemoryScope
from phronesis.memory.vector import InMemoryVectorStore, VectorItem, VectorStore


class TestProtocol:
    def test_implements_protocol(self) -> None:
        assert isinstance(InMemoryVectorStore(), VectorStore)


def _item(ident: str, embedding: tuple[float, ...], text: str = "t") -> VectorItem:
    return VectorItem(id=ident, text=text, embedding=embedding, metadata={})


class TestUpsertSearch:
    @pytest.mark.asyncio
    async def test_search_orders_by_descending_score(self, session_scope: MemoryScope) -> None:
        store = InMemoryVectorStore()

        await store.upsert(
            session_scope,
            (
                _item("a", (1.0, 0.0)),
                _item("b", (0.0, 1.0)),
                _item("c", (0.9, 0.1)),
            ),
        )

        results = await store.search(session_scope, (1.0, 0.0), k=3)

        assert tuple(item.id for item, _ in results) == ("a", "c", "b")

    @pytest.mark.asyncio
    async def test_search_truncates_to_k(self, session_scope: MemoryScope) -> None:
        store = InMemoryVectorStore()

        await store.upsert(
            session_scope,
            (_item("a", (1.0, 0.0)), _item("b", (0.0, 1.0))),
        )

        results = await store.search(session_scope, (1.0, 0.0), k=1)

        assert len(results) == 1
        assert results[0][0].id == "a"

    @pytest.mark.asyncio
    async def test_search_filters_by_min_score(self, session_scope: MemoryScope) -> None:
        store = InMemoryVectorStore()

        await store.upsert(
            session_scope,
            (_item("a", (1.0, 0.0)), _item("b", (0.0, 1.0))),
        )

        results = await store.search(session_scope, (1.0, 0.0), k=5, min_score=0.5)

        assert tuple(item.id for item, _ in results) == ("a",)

    @pytest.mark.asyncio
    async def test_search_with_zero_k_returns_empty(self, session_scope: MemoryScope) -> None:
        store = InMemoryVectorStore()

        await store.upsert(session_scope, (_item("a", (1.0, 0.0)),))

        assert await store.search(session_scope, (1.0, 0.0), k=0) == ()

    @pytest.mark.asyncio
    async def test_upsert_overwrites_by_id(self, session_scope: MemoryScope) -> None:
        store = InMemoryVectorStore()

        await store.upsert(session_scope, (_item("a", (1.0, 0.0), text="old"),))
        await store.upsert(session_scope, (_item("a", (0.0, 1.0), text="new"),))

        assert await store.count(session_scope) == 1

        results = await store.search(session_scope, (0.0, 1.0), k=1)

        assert results[0][0].text == "new"


class TestDeleteCount:
    @pytest.mark.asyncio
    async def test_delete_returns_count_removed(self, session_scope: MemoryScope) -> None:
        store = InMemoryVectorStore()

        await store.upsert(
            session_scope,
            (_item("a", (1.0, 0.0)), _item("b", (0.0, 1.0))),
        )

        assert await store.delete(session_scope, ("a", "missing")) == 1
        assert await store.count(session_scope) == 1

    @pytest.mark.asyncio
    async def test_delete_on_empty_scope_returns_zero(self, session_scope: MemoryScope) -> None:
        store = InMemoryVectorStore()

        assert await store.delete(session_scope, ("x",)) == 0

    @pytest.mark.asyncio
    async def test_count_on_empty_scope_returns_zero(self, session_scope: MemoryScope) -> None:
        store = InMemoryVectorStore()

        assert await store.count(session_scope) == 0


class TestScopeIsolation:
    @pytest.mark.asyncio
    async def test_writes_to_one_scope_do_not_leak(self) -> None:
        store = InMemoryVectorStore()
        a = MemoryScope.session("SID_a")
        b = MemoryScope.session("SID_b")

        await store.upsert(a, (_item("x", (1.0, 0.0)),))

        assert await store.count(b) == 0
