"""Tests for the MISSING sentinel."""

from typing import Any

from phronesis._internal.typing import MISSING


class TestMissing:
    def test_is_distinct_from_none(self) -> None:
        assert MISSING is not None

    def test_is_falsy(self) -> None:
        assert bool(MISSING) is False

    def test_is_singleton_across_imports(self) -> None:
        from phronesis._internal.typing import MISSING as MISSING_AGAIN

        assert MISSING is MISSING_AGAIN

    def test_repr_is_descriptive(self) -> None:
        assert repr(MISSING) == "MISSING"

    def test_can_be_used_as_default_argument(self) -> None:
        def f(x: Any = MISSING) -> Any:
            return x

        assert f() is MISSING
        assert f(None) is None
        assert f(0) == 0
