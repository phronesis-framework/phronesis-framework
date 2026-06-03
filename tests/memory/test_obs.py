"""Tests for :mod:`phronesis.memory.obs`."""

from __future__ import annotations

import pytest

from phronesis.memory.obs import (
    BACKEND_IN_MEMORY,
    MEMORY_OP,
    MEMORY_SCOPE_ID,
    MEMORY_SCOPE_LEVEL,
    MEMORY_STORE_BACKEND,
    MEMORY_STORE_TYPE,
    STORE_TYPE_KV,
    memory_span,
    scope_attributes,
)
from phronesis.memory.scope import MemoryScope


class TestConstants:
    def test_attribute_keys_are_stable(self) -> None:
        assert MEMORY_OP == "memory.op"
        assert MEMORY_STORE_TYPE == "memory.store.type"
        assert MEMORY_STORE_BACKEND == "memory.store.backend"
        assert MEMORY_SCOPE_LEVEL == "memory.scope.level"
        assert MEMORY_SCOPE_ID == "memory.scope.id"


class TestScopeAttributes:
    def test_global_scope_omits_id(self) -> None:
        attrs = scope_attributes(MemoryScope.global_())

        assert attrs == {MEMORY_SCOPE_LEVEL: "global"}

    def test_session_scope_includes_id(self) -> None:
        attrs = scope_attributes(MemoryScope.session("SID_x"))

        assert attrs == {
            MEMORY_SCOPE_LEVEL: "session",
            MEMORY_SCOPE_ID: "SID_x",
        }


class TestMemorySpan:
    @pytest.mark.asyncio
    async def test_span_yields_object(self, session_scope: MemoryScope) -> None:
        async with memory_span(
            "get",
            store_type=STORE_TYPE_KV,
            backend=BACKEND_IN_MEMORY,
            scope=session_scope,
        ) as span:
            assert span is not None

    @pytest.mark.asyncio
    async def test_span_accepts_extra_attributes(self, session_scope: MemoryScope) -> None:
        async with memory_span(
            "search",
            store_type=STORE_TYPE_KV,
            backend=BACKEND_IN_MEMORY,
            scope=session_scope,
            extra={"memory.search.top_k": 5},
        ) as span:
            assert span is not None
