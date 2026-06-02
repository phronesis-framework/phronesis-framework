"""Tests for :class:`phronesis.memory.InMemoryWorkingStore`."""

from __future__ import annotations

import pytest

from phronesis.memory.scope import MemoryScope
from phronesis.memory.working import InMemoryWorkingStore, WorkingMemoryStore


class TestProtocolConformance:
    def test_in_memory_store_implements_protocol(self) -> None:
        store = InMemoryWorkingStore()

        assert isinstance(store, WorkingMemoryStore)


class TestSetGet:
    @pytest.mark.asyncio
    async def test_set_then_get_returns_value(self, session_scope: MemoryScope) -> None:
        store = InMemoryWorkingStore()

        await store.set(session_scope, "plan", "step 1")

        assert await store.get(session_scope, "plan") == "step 1"

    @pytest.mark.asyncio
    async def test_get_missing_key_returns_none(self, session_scope: MemoryScope) -> None:
        store = InMemoryWorkingStore()

        assert await store.get(session_scope, "missing") is None

    @pytest.mark.asyncio
    async def test_set_overwrites_prior_value(self, session_scope: MemoryScope) -> None:
        store = InMemoryWorkingStore()

        await store.set(session_scope, "k", "v1")
        await store.set(session_scope, "k", "v2")

        assert await store.get(session_scope, "k") == "v2"


class TestAppend:
    @pytest.mark.asyncio
    async def test_append_creates_list(self, session_scope: MemoryScope) -> None:
        store = InMemoryWorkingStore()

        await store.append(session_scope, "log", "entry-1")

        assert await store.get(session_scope, "log") == ["entry-1"]

    @pytest.mark.asyncio
    async def test_append_extends_existing_list(self, session_scope: MemoryScope) -> None:
        store = InMemoryWorkingStore()

        await store.append(session_scope, "log", "a")
        await store.append(session_scope, "log", "b")

        assert await store.get(session_scope, "log") == ["a", "b"]

    @pytest.mark.asyncio
    async def test_append_on_non_list_raises(self, session_scope: MemoryScope) -> None:
        store = InMemoryWorkingStore()

        await store.set(session_scope, "k", 1)

        with pytest.raises(TypeError):
            await store.append(session_scope, "k", "x")


class TestListAndClear:
    @pytest.mark.asyncio
    async def test_list_keys_returns_sorted_keys(self, session_scope: MemoryScope) -> None:
        store = InMemoryWorkingStore()

        await store.set(session_scope, "b", 1)
        await store.set(session_scope, "a", 2)

        assert await store.list_keys(session_scope) == ("a", "b")

    @pytest.mark.asyncio
    async def test_clear_removes_all_keys(self, session_scope: MemoryScope) -> None:
        store = InMemoryWorkingStore()

        await store.set(session_scope, "a", 1)
        await store.clear(session_scope)

        assert await store.list_keys(session_scope) == ()


class TestSnapshotRestore:
    @pytest.mark.asyncio
    async def test_snapshot_then_restore_round_trips(self, session_scope: MemoryScope) -> None:
        store = InMemoryWorkingStore()

        await store.set(session_scope, "k", "v")
        await store.append(session_scope, "log", "a")
        snap = await store.snapshot(session_scope)

        await store.clear(session_scope)
        await store.restore(session_scope, snap)

        assert await store.get(session_scope, "k") == "v"
        assert await store.get(session_scope, "log") == ["a"]

    @pytest.mark.asyncio
    async def test_snapshot_copies_lists(self, session_scope: MemoryScope) -> None:
        store = InMemoryWorkingStore()

        await store.append(session_scope, "log", "a")
        snap = await store.snapshot(session_scope)
        snap["log"].append("X")

        assert await store.get(session_scope, "log") == ["a"]


class TestScopeIsolation:
    @pytest.mark.asyncio
    async def test_writes_to_one_scope_do_not_leak(self) -> None:
        store = InMemoryWorkingStore()
        a = MemoryScope.session("SID_a")
        b = MemoryScope.session("SID_b")

        await store.set(a, "k", 1)

        assert await store.get(b, "k") is None
