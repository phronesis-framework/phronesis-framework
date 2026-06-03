"""Tests for :class:`phronesis.memory.MemoryPersistenceHook`."""

from __future__ import annotations

import pytest

from phronesis.agents.run import Result, RunId
from phronesis.memory.episodic import InMemoryEpisodicStore
from phronesis.memory.hooks import MemoryPersistenceHook
from phronesis.memory.kv import InMemoryKeyValueStore
from phronesis.memory.scope import MemoryScope
from phronesis.memory.working import InMemoryWorkingStore
from phronesis.providers.usage import TokenUsage


def _result(canonical: str = "phronesis.agents.run.rid_test") -> Result:
    return Result(
        run_id=RunId(canonical),
        output="ok",
        tokens=TokenUsage(),
        iterations=3,
        tool_calls=(),
        messages=(),
        success=True,
    )


class TestPersistence:
    @pytest.mark.asyncio
    async def test_snapshot_is_written_to_kv(self) -> None:
        working = InMemoryWorkingStore()
        kv = InMemoryKeyValueStore()
        scope = MemoryScope.run("RID_x")

        await working.set(scope, "k", "v")

        hook = MemoryPersistenceHook(working, kv, scope_fn=lambda _: scope)

        await hook(_result())

        stored = await kv.get(scope, "last_working_snapshot")

        assert stored == {"k": "v"}

    @pytest.mark.asyncio
    async def test_default_scope_derives_from_run_id(self) -> None:
        working = InMemoryWorkingStore()
        kv = InMemoryKeyValueStore()

        hook = MemoryPersistenceHook(working, kv)
        result = _result()

        await hook(result)

        scope = MemoryScope.run(result.run_id.canonical)

        assert await kv.get(scope, "last_working_snapshot") == {}

    @pytest.mark.asyncio
    async def test_episode_recorded_when_episodic_provided(self) -> None:
        working = InMemoryWorkingStore()
        kv = InMemoryKeyValueStore()
        episodic = InMemoryEpisodicStore()
        scope = MemoryScope.run("RID_x")

        hook = MemoryPersistenceHook(working, kv, episodic, scope_fn=lambda _: scope)

        await hook(_result())

        latest = await episodic.latest(scope, "run_completed")

        assert latest is not None
        assert latest.payload["iterations"] == 3
        assert latest.payload["success"] is True

    @pytest.mark.asyncio
    async def test_no_episode_when_episodic_absent(self) -> None:
        working = InMemoryWorkingStore()
        kv = InMemoryKeyValueStore()
        scope = MemoryScope.run("RID_x")

        hook = MemoryPersistenceHook(working, kv, scope_fn=lambda _: scope)

        await hook(_result())

    @pytest.mark.asyncio
    async def test_custom_snapshot_key(self) -> None:
        working = InMemoryWorkingStore()
        kv = InMemoryKeyValueStore()
        scope = MemoryScope.run("RID_x")

        await working.set(scope, "k", "v")

        hook = MemoryPersistenceHook(
            working,
            kv,
            scope_fn=lambda _: scope,
            snapshot_key="custom_key",
        )

        await hook(_result())

        assert await kv.get(scope, "custom_key") == {"k": "v"}
