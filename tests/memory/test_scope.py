"""Tests for :class:`phronesis.memory.MemoryScope`."""

from __future__ import annotations

import pytest

from phronesis.memory.errors import MemoryScopeError
from phronesis.memory.scope import MemoryLevel, MemoryScope


class TestConstructors:
    def test_global_helper_returns_global_scope(self) -> None:
        scope = MemoryScope.global_()

        assert scope.level is MemoryLevel.GLOBAL
        assert scope.id is None

    def test_agent_helper_returns_agent_scope(self) -> None:
        scope = MemoryScope.agent("AID_x")

        assert scope.level is MemoryLevel.AGENT
        assert scope.id == "AID_x"

    def test_session_helper_returns_session_scope(self) -> None:
        scope = MemoryScope.session("SID_x")

        assert scope.level is MemoryLevel.SESSION
        assert scope.id == "SID_x"

    def test_run_helper_returns_run_scope(self) -> None:
        scope = MemoryScope.run("RID_x")

        assert scope.level is MemoryLevel.RUN
        assert scope.id == "RID_x"

    def test_pipeline_run_helper_returns_pipeline_run_scope(self) -> None:
        scope = MemoryScope.pipeline_run("PRID_x")

        assert scope.level is MemoryLevel.PIPELINE_RUN
        assert scope.id == "PRID_x"


class TestValidation:
    def test_global_with_id_raises(self) -> None:
        with pytest.raises(MemoryScopeError):
            MemoryScope(level=MemoryLevel.GLOBAL, id="anything")

    def test_non_global_without_id_raises(self) -> None:
        with pytest.raises(MemoryScopeError):
            MemoryScope(level=MemoryLevel.SESSION, id=None)

    def test_non_global_with_empty_id_raises(self) -> None:
        with pytest.raises(MemoryScopeError):
            MemoryScope(level=MemoryLevel.SESSION, id="")


class TestEqualityAndHashing:
    def test_equal_scopes_compare_equal(self) -> None:
        a = MemoryScope.session("SID_x")
        b = MemoryScope.session("SID_x")

        assert a == b

    def test_different_id_compares_not_equal(self) -> None:
        a = MemoryScope.session("SID_x")
        b = MemoryScope.session("SID_y")

        assert a != b

    def test_scope_is_hashable(self) -> None:
        scope = MemoryScope.session("SID_x")

        assert hash(scope) == hash(MemoryScope.session("SID_x"))


class TestKey:
    def test_global_key_omits_id(self) -> None:
        assert MemoryScope.global_().key == "global"

    def test_scoped_key_includes_id(self) -> None:
        assert MemoryScope.session("SID_x").key == "session:SID_x"
