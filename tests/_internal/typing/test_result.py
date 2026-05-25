"""Tests for the Result ADT."""

from dataclasses import FrozenInstanceError

import pytest

from phronesis._internal.typing import Err, Ok, Result


class TestOk:
    def test_holds_value(self) -> None:
        ok: Ok[int] = Ok(42)

        assert ok.value == 42

    def test_is_frozen(self) -> None:
        ok: Ok[int] = Ok(1)

        with pytest.raises(FrozenInstanceError):
            ok.value = 2  # type: ignore[misc]

    def test_equality_by_value(self) -> None:
        assert Ok(1) == Ok(1)
        assert Ok(1) != Ok(2)


class TestErr:
    def test_holds_error(self) -> None:
        err: Err[str] = Err("boom")

        assert err.error == "boom"

    def test_is_frozen(self) -> None:
        err: Err[str] = Err("x")

        with pytest.raises(FrozenInstanceError):
            err.error = "y"  # type: ignore[misc]

    def test_equality_by_error(self) -> None:
        assert Err("a") == Err("a")
        assert Err("a") != Err("b")


class TestResultPatternMatch:
    def test_match_ok(self) -> None:
        result: Result[int, str] = Ok(10)

        match result:
            case Ok(value):
                assert value == 10
            case Err(_):
                pytest.fail("should not match Err")

    def test_match_err(self) -> None:
        result: Result[int, str] = Err("oops")

        match result:
            case Ok(_):
                pytest.fail("should not match Ok")
            case Err(error):
                assert error == "oops"

    def test_ok_and_err_are_disjoint(self) -> None:
        left: object = Ok(1)
        right: object = Err(1)

        assert left != right
