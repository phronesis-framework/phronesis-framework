"""Tests for CanonicalIdValidator."""

import pytest

from phronesis._internal.ids import CanonicalIdValidator


class TestCanonicalIdValidator:
    @pytest.mark.parametrize(
        "value",
        [
            "search_web",
            "my_app.tools.web.search_web",
            "acme.search",
            "a.b.c.d.e",
            "_internal",
            "phronesis._internal.ids._sample",
            "_a._b._c",
        ],
    )
    def test_accepts_valid_ids(self, value: str) -> None:
        CanonicalIdValidator.validate(value)

    @pytest.mark.parametrize(
        "value",
        [
            "",
            "Search_Web",
            "123_tool",
            "my.app.",
            ".my.app",
            "my..app",
            "my-app",
            "my app",
        ],
    )
    def test_rejects_invalid_ids(self, value: str) -> None:
        with pytest.raises(ValueError):
            CanonicalIdValidator.validate(value)
