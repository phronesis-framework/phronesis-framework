"""Tests for :class:`phronesis.memory.Checkpointer`."""

from __future__ import annotations

import asyncio

import pytest

from phronesis.memory.checkpoint import (
    CHECKPOINT_RESTORED_TYPE,
    CHECKPOINT_TYPE,
    Checkpointer,
)
from phronesis.memory.episodic import InMemoryEpisodicStore
from phronesis.memory.errors import CheckpointNotFoundError
from phronesis.memory.scope import MemoryScope
from phronesis.memory.working import InMemoryWorkingStore


def _make() -> tuple[Checkpointer, InMemoryWorkingStore, InMemoryEpisodicStore]:
    working = InMemoryWorkingStore()
    episodic = InMemoryEpisodicStore()

    return Checkpointer(working, episodic), working, episodic


class TestSave:
    @pytest.mark.asyncio
    async def test_save_returns_checkpoint_with_snapshot(self, session_scope: MemoryScope) -> None:
        cp, working, _ = _make()

        await working.set(session_scope, "k", "v")

        checkpoint = await cp.save(session_scope, cursor={"step": 1})

        assert checkpoint.working_snapshot["k"] == "v"
        assert checkpoint.cursor["step"] == 1
        assert checkpoint.scope == session_scope

    @pytest.mark.asyncio
    async def test_save_records_checkpoint_episode(self, session_scope: MemoryScope) -> None:
        cp, _, episodic = _make()

        checkpoint = await cp.save(session_scope)

        latest = await episodic.latest(session_scope, CHECKPOINT_TYPE)

        assert latest is not None
        assert latest.payload["checkpoint_id"] == checkpoint.checkpoint_id

    @pytest.mark.asyncio
    async def test_save_with_default_cursor_is_empty(self, session_scope: MemoryScope) -> None:
        cp, _, _ = _make()

        checkpoint = await cp.save(session_scope)

        assert dict(checkpoint.cursor) == {}


class TestLoad:
    @pytest.mark.asyncio
    async def test_load_none_returns_latest(self, session_scope: MemoryScope) -> None:
        cp, _, _ = _make()

        await cp.save(session_scope, cursor={"step": 1})
        await asyncio.sleep(0.01)
        second = await cp.save(session_scope, cursor={"step": 2})

        latest = await cp.load(session_scope)

        assert latest is not None
        assert latest.checkpoint_id == second.checkpoint_id

    @pytest.mark.asyncio
    async def test_load_none_returns_none_when_empty(self, session_scope: MemoryScope) -> None:
        cp, _, _ = _make()

        assert await cp.load(session_scope) is None

    @pytest.mark.asyncio
    async def test_load_by_id_returns_matching(self, session_scope: MemoryScope) -> None:
        cp, _, _ = _make()

        first = await cp.save(session_scope, cursor={"step": 1})
        await cp.save(session_scope, cursor={"step": 2})

        loaded = await cp.load(session_scope, first.checkpoint_id)

        assert loaded is not None
        assert loaded.cursor["step"] == 1

    @pytest.mark.asyncio
    async def test_load_missing_id_raises(self, session_scope: MemoryScope) -> None:
        cp, _, _ = _make()

        await cp.save(session_scope)

        with pytest.raises(CheckpointNotFoundError):
            await cp.load(session_scope, "chk_missing")


class TestRestore:
    @pytest.mark.asyncio
    async def test_restore_overwrites_working_memory(self, session_scope: MemoryScope) -> None:
        cp, working, _ = _make()

        await working.set(session_scope, "k", "v")
        await cp.save(session_scope)

        await working.set(session_scope, "k", "mutated")
        await working.set(session_scope, "extra", "x")

        await cp.restore(session_scope)

        assert await working.get(session_scope, "k") == "v"
        assert await working.get(session_scope, "extra") is None

    @pytest.mark.asyncio
    async def test_restore_emits_restored_episode(self, session_scope: MemoryScope) -> None:
        cp, _, episodic = _make()

        await cp.save(session_scope)
        await cp.restore(session_scope)

        latest = await episodic.latest(session_scope, CHECKPOINT_RESTORED_TYPE)

        assert latest is not None

    @pytest.mark.asyncio
    async def test_restore_when_no_checkpoint_returns_none(
        self, session_scope: MemoryScope
    ) -> None:
        cp, _, _ = _make()

        assert await cp.restore(session_scope) is None
