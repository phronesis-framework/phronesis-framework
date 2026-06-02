"""Tests for :class:`phronesis.memory.InMemoryEpisodicStore`."""

from __future__ import annotations

import pytest

from phronesis.memory.episodic import Episode, EpisodicStore, InMemoryEpisodicStore
from phronesis.memory.scope import MemoryScope


def _ep(
    scope: MemoryScope,
    *,
    eid: str = "E_x",
    ts: float = 0.0,
    type: str = "run_started",
    payload: dict[str, object] | None = None,
) -> Episode:
    return Episode(
        episode_id=eid,
        scope=scope,
        timestamp=ts,
        type=type,
        payload=payload or {},
    )


class TestProtocol:
    def test_implements_protocol(self) -> None:
        assert isinstance(InMemoryEpisodicStore(), EpisodicStore)


class TestRecordQuery:
    @pytest.mark.asyncio
    async def test_query_returns_in_timestamp_order(self, session_scope: MemoryScope) -> None:
        store = InMemoryEpisodicStore()

        await store.record(_ep(session_scope, eid="a", ts=2.0))
        await store.record(_ep(session_scope, eid="b", ts=1.0))

        results = await store.query(session_scope)

        assert tuple(ep.episode_id for ep in results) == ("b", "a")

    @pytest.mark.asyncio
    async def test_query_filters_by_type(self, session_scope: MemoryScope) -> None:
        store = InMemoryEpisodicStore()

        await store.record(_ep(session_scope, eid="a", ts=1.0, type="run_started"))
        await store.record(_ep(session_scope, eid="b", ts=2.0, type="tool_call"))

        results = await store.query(session_scope, types=("tool_call",))

        assert tuple(ep.episode_id for ep in results) == ("b",)

    @pytest.mark.asyncio
    async def test_query_filters_by_since(self, session_scope: MemoryScope) -> None:
        store = InMemoryEpisodicStore()

        await store.record(_ep(session_scope, eid="a", ts=1.0))
        await store.record(_ep(session_scope, eid="b", ts=5.0))

        results = await store.query(session_scope, since=2.0)

        assert tuple(ep.episode_id for ep in results) == ("b",)

    @pytest.mark.asyncio
    async def test_query_with_zero_limit_returns_empty(self, session_scope: MemoryScope) -> None:
        store = InMemoryEpisodicStore()

        await store.record(_ep(session_scope))

        assert await store.query(session_scope, limit=0) == ()

    @pytest.mark.asyncio
    async def test_query_respects_limit(self, session_scope: MemoryScope) -> None:
        store = InMemoryEpisodicStore()

        for i in range(5):
            await store.record(_ep(session_scope, eid=f"e{i}", ts=float(i)))

        results = await store.query(session_scope, limit=2)

        assert len(results) == 2


class TestLatest:
    @pytest.mark.asyncio
    async def test_latest_returns_most_recent_of_type(self, session_scope: MemoryScope) -> None:
        store = InMemoryEpisodicStore()

        await store.record(_ep(session_scope, eid="old", ts=1.0, type="x"))
        await store.record(_ep(session_scope, eid="new", ts=2.0, type="x"))
        await store.record(_ep(session_scope, eid="other", ts=3.0, type="y"))

        latest = await store.latest(session_scope, "x")

        assert latest is not None
        assert latest.episode_id == "new"

    @pytest.mark.asyncio
    async def test_latest_returns_none_when_absent(self, session_scope: MemoryScope) -> None:
        store = InMemoryEpisodicStore()

        assert await store.latest(session_scope, "x") is None


class TestDelete:
    @pytest.mark.asyncio
    async def test_delete_returns_count(self, session_scope: MemoryScope) -> None:
        store = InMemoryEpisodicStore()

        await store.record(_ep(session_scope, eid="a"))
        await store.record(_ep(session_scope, eid="b"))

        assert await store.delete(session_scope) == 2
        assert await store.query(session_scope) == ()

    @pytest.mark.asyncio
    async def test_delete_empty_scope_returns_zero(self, session_scope: MemoryScope) -> None:
        store = InMemoryEpisodicStore()

        assert await store.delete(session_scope) == 0
