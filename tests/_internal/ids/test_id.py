"""Tests for Id."""

import pytest

from phronesis._internal.ids import Id


class _FakeId(Id):
    prefix = "FID"


class TestId:
    def test_canonical_is_exposed(self) -> None:
        fid = _FakeId("my.entity")

        assert fid.canonical == "my.entity"

    def test_short_has_prefix_and_hash(self) -> None:
        fid = _FakeId("my.entity")

        assert fid.short.startswith("FID-")
        assert len(fid.short) == len("FID-") + 8

    def test_short_is_deterministic(self) -> None:
        a = _FakeId("my.entity")
        b = _FakeId("my.entity")

        assert a.short == b.short

    def test_str_returns_canonical(self) -> None:
        fid = _FakeId("my.entity")

        assert str(fid) == "my.entity"

    def test_equality_by_value(self) -> None:
        assert _FakeId("a.b") == _FakeId("a.b")
        assert _FakeId("a.b") != _FakeId("a.c")

    def test_is_hashable(self) -> None:
        fid = _FakeId("a.b")

        assert fid.__hash__() is not None

    def test_rejects_invalid_canonical(self) -> None:
        with pytest.raises(ValueError):
            _FakeId("Invalid Id")

    def test_subclass_must_define_prefix(self) -> None:
        class WithoutPrefix(Id):
            pass

        with pytest.raises(TypeError):
            WithoutPrefix("my.entity")
