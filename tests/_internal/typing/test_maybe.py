"""Tests for the Maybe ADT."""

from dataclasses import FrozenInstanceError

import pytest

from phronesis._internal.typing import NOTHING, Maybe, Some


class TestSome:
    def test_holds_value(self) -> None:
        some: Some[int] = Some(5)
        assert some.value == 5

    def test_is_frozen(self) -> None:
        some: Some[int] = Some(1)
        with pytest.raises(FrozenInstanceError):
            some.value = 2  # type: ignore[misc]

    def test_equality_by_value(self) -> None:
        assert Some("a") == Some("a")
        assert Some("a") != Some("b")


class TestNothing:
    def test_is_singleton_across_imports(self) -> None:
        from phronesis._internal.typing import NOTHING as NOTHING_AGAIN

        assert NOTHING is NOTHING_AGAIN

    def test_is_falsy(self) -> None:
        assert bool(NOTHING) is False

    def test_repr_is_descriptive(self) -> None:
        assert repr(NOTHING) == "NOTHING"


class TestMaybePatternMatch:
    def test_match_some(self) -> None:
        m: Maybe[int] = Some(7)
        match m:
            case Some(v):
                assert v == 7
            case _:
                pytest.fail("should match Some")

    def test_match_nothing(self) -> None:
        m: Maybe[int] = NOTHING
        match m:
            case Some(_):
                pytest.fail("should not match Some")
            case _:
                assert m is NOTHING
