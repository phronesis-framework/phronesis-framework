"""Tests for IdGenerator."""

from typing import ClassVar

from phronesis._internal.ids import Id, IdGenerator


class _FakeId(Id):
    prefix: ClassVar[str] = "FID"


def _sample_function() -> None:
    """Used by test_from_function below."""


class TestIdGenerator:
    def test_from_function_uses_module_and_qualname(self) -> None:
        gen = IdGenerator(_FakeId)
        fid = gen.from_function(_sample_function)
        assert _sample_function.__module__ in fid.canonical
        assert _sample_function.__qualname__.lower() in fid.canonical

    def test_from_function_returns_correct_type(self) -> None:
        gen = IdGenerator(_FakeId)
        fid = gen.from_function(_sample_function)
        assert isinstance(fid, _FakeId)

    def test_from_canonical_returns_correct_type(self) -> None:
        gen = IdGenerator(_FakeId)
        fid = gen.from_canonical("my.entity")
        assert isinstance(fid, _FakeId)
        assert fid.canonical == "my.entity"

    def test_from_canonical_validates(self) -> None:
        import pytest

        gen = IdGenerator(_FakeId)
        with pytest.raises(ValueError):
            gen.from_canonical("Invalid Id")
