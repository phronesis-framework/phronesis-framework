"""Tests for :class:`phronesis.memory.InMemoryKeyValueStore`."""

from __future__ import annotations

import asyncio

import pytest

from phronesis.memory.kv import InMemoryKeyValueStore, KeyValueStore
from phronesis.memory.scope import MemoryScope


class TestProtocol:
    def test_backend_implements_protocol(self) -> None:
        assert isinstance(InMemoryKeyValueStore(), KeyValueStore)


class TestBasicOps:
    @pytest.mark.asyncio
    async def test_set_then_get(self, session_scope: MemoryScope) -> None:
        kv = InMemoryKeyValueStore()

        await kv.set(session_scope, "user.name", "alice")

        assert await kv.get(session_scope, "user.name") == "alice"

    @pytest.mark.asyncio
    async def test_missing_key_returns_none(self, session_scope: MemoryScope) -> None:
        kv = InMemoryKeyValueStore()

        assert await kv.get(session_scope, "missing") is None

    @pytest.mark.asyncio
    async def test_delete_existing_returns_true(self, session_scope: MemoryScope) -> None:
        kv = InMemoryKeyValueStore()

        await kv.set(session_scope, "k", "v")

        assert await kv.delete(session_scope, "k") is True
        assert await kv.get(session_scope, "k") is None

    @pytest.mark.asyncio
    async def test_delete_missing_returns_false(self, session_scope: MemoryScope) -> None:
        kv = InMemoryKeyValueStore()

        assert await kv.delete(session_scope, "missing") is False

    @pytest.mark.asyncio
    async def test_list_keys_with_prefix(self, session_scope: MemoryScope) -> None:
        kv = InMemoryKeyValueStore()

        await kv.set(session_scope, "user.name", "alice")
        await kv.set(session_scope, "user.email", "a@x")
        await kv.set(session_scope, "other", "x")

        assert await kv.list_keys(session_scope, prefix="user.") == (
            "user.email",
            "user.name",
        )


class TestCompareAndSwap:
    @pytest.mark.asyncio
    async def test_cas_swaps_when_expected_matches(self, session_scope: MemoryScope) -> None:
        kv = InMemoryKeyValueStore()

        await kv.set(session_scope, "lock", "free")

        assert await kv.compare_and_swap(session_scope, "lock", "free", "held") is True
        assert await kv.get(session_scope, "lock") == "held"

    @pytest.mark.asyncio
    async def test_cas_fails_when_expected_does_not_match(self, session_scope: MemoryScope) -> None:
        kv = InMemoryKeyValueStore()

        await kv.set(session_scope, "lock", "held")

        assert await kv.compare_and_swap(session_scope, "lock", "free", "x") is False
        assert await kv.get(session_scope, "lock") == "held"

    @pytest.mark.asyncio
    async def test_cas_on_missing_key_treats_current_as_none(
        self, session_scope: MemoryScope
    ) -> None:
        kv = InMemoryKeyValueStore()

        assert await kv.compare_and_swap(session_scope, "lock", None, "held") is True
        assert await kv.get(session_scope, "lock") == "held"


class TestAppendIncrement:
    @pytest.mark.asyncio
    async def test_append_creates_list(self, session_scope: MemoryScope) -> None:
        kv = InMemoryKeyValueStore()

        await kv.append(session_scope, "log", "a")

        assert await kv.get(session_scope, "log") == ["a"]

    @pytest.mark.asyncio
    async def test_increment_creates_then_increments(self, session_scope: MemoryScope) -> None:
        kv = InMemoryKeyValueStore()

        assert await kv.increment(session_scope, "counter") == 1
        assert await kv.increment(session_scope, "counter", delta=5) == 6

    @pytest.mark.asyncio
    async def test_increment_on_non_int_raises(self, session_scope: MemoryScope) -> None:
        kv = InMemoryKeyValueStore()

        await kv.set(session_scope, "k", "not-int")

        with pytest.raises(TypeError):
            await kv.increment(session_scope, "k")

    @pytest.mark.asyncio
    async def test_append_on_non_list_raises(self, session_scope: MemoryScope) -> None:
        kv = InMemoryKeyValueStore()

        await kv.set(session_scope, "k", 1)

        with pytest.raises(TypeError):
            await kv.append(session_scope, "k", "x")


class TestTTL:
    @pytest.mark.asyncio
    async def test_value_expires_after_ttl(self, session_scope: MemoryScope) -> None:
        kv = InMemoryKeyValueStore()

        await kv.set(session_scope, "k", "v", ttl_s=0.01)
        await asyncio.sleep(0.02)

        assert await kv.get(session_scope, "k") is None

    @pytest.mark.asyncio
    async def test_value_present_before_ttl(self, session_scope: MemoryScope) -> None:
        kv = InMemoryKeyValueStore()

        await kv.set(session_scope, "k", "v", ttl_s=5)

        assert await kv.get(session_scope, "k") == "v"

    @pytest.mark.asyncio
    async def test_expired_key_excluded_from_list(self, session_scope: MemoryScope) -> None:
        kv = InMemoryKeyValueStore()

        await kv.set(session_scope, "k", "v", ttl_s=0.01)
        await asyncio.sleep(0.02)

        assert await kv.list_keys(session_scope) == ()
