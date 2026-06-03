"""Tests for :class:`phronesis.memory.FilesystemJSONVectorStore`."""

from __future__ import annotations

from pathlib import Path

import pytest

from phronesis.memory.errors import MemoryBackendError
from phronesis.memory.scope import MemoryScope
from phronesis.memory.vector import (
    FilesystemJSONVectorStore,
    VectorItem,
    VectorStore,
)


def _item(ident: str, embedding: tuple[float, ...], text: str = "t") -> VectorItem:
    return VectorItem(id=ident, text=text, embedding=embedding, metadata={})


class TestProtocol:
    def test_implements_protocol(self, tmp_path: Path) -> None:
        assert isinstance(FilesystemJSONVectorStore(tmp_path), VectorStore)


class TestPersistence:
    @pytest.mark.asyncio
    async def test_items_persist_across_instances(
        self, tmp_path: Path, session_scope: MemoryScope
    ) -> None:
        first = FilesystemJSONVectorStore(tmp_path)
        await first.upsert(session_scope, (_item("a", (1.0, 0.0), text="hello"),))

        second = FilesystemJSONVectorStore(tmp_path)

        assert await second.count(session_scope) == 1

        results = await second.search(session_scope, (1.0, 0.0), k=1)

        assert results[0][0].text == "hello"

    @pytest.mark.asyncio
    async def test_atomic_write_leaves_no_tmp_files(
        self, tmp_path: Path, session_scope: MemoryScope
    ) -> None:
        store = FilesystemJSONVectorStore(tmp_path)

        await store.upsert(session_scope, (_item("a", (1.0, 0.0)),))

        stray = [p for p in (tmp_path / "session").iterdir() if p.name.startswith(".tmp-")]

        assert stray == []


class TestOps:
    @pytest.mark.asyncio
    async def test_upsert_overwrites_by_id(
        self, tmp_path: Path, session_scope: MemoryScope
    ) -> None:
        store = FilesystemJSONVectorStore(tmp_path)

        await store.upsert(session_scope, (_item("a", (1.0, 0.0), text="old"),))
        await store.upsert(session_scope, (_item("a", (0.0, 1.0), text="new"),))

        assert await store.count(session_scope) == 1

        results = await store.search(session_scope, (0.0, 1.0), k=1)

        assert results[0][0].text == "new"

    @pytest.mark.asyncio
    async def test_search_filters_by_min_score(
        self, tmp_path: Path, session_scope: MemoryScope
    ) -> None:
        store = FilesystemJSONVectorStore(tmp_path)

        await store.upsert(
            session_scope,
            (_item("a", (1.0, 0.0)), _item("b", (0.0, 1.0))),
        )

        results = await store.search(session_scope, (1.0, 0.0), k=5, min_score=0.5)

        assert tuple(item.id for item, _ in results) == ("a",)

    @pytest.mark.asyncio
    async def test_delete_returns_count_removed(
        self, tmp_path: Path, session_scope: MemoryScope
    ) -> None:
        store = FilesystemJSONVectorStore(tmp_path)

        await store.upsert(
            session_scope,
            (_item("a", (1.0, 0.0)), _item("b", (0.0, 1.0))),
        )

        assert await store.delete(session_scope, ("a", "missing")) == 1
        assert await store.count(session_scope) == 1

    @pytest.mark.asyncio
    async def test_global_scope_uses_dedicated_file(self, tmp_path: Path) -> None:
        store = FilesystemJSONVectorStore(tmp_path)

        await store.upsert(MemoryScope.global_(), (_item("a", (1.0, 0.0)),))

        assert (tmp_path / "global.jsonl").exists()


class TestCorruption:
    @pytest.mark.asyncio
    async def test_invalid_json_raises_backend_error(
        self, tmp_path: Path, session_scope: MemoryScope
    ) -> None:
        store = FilesystemJSONVectorStore(tmp_path)

        path = tmp_path / "session" / "SID_test.jsonl"
        path.parent.mkdir(parents=True)
        path.write_text("not json\n", encoding="utf-8")

        with pytest.raises(MemoryBackendError):
            await store.count(session_scope)
