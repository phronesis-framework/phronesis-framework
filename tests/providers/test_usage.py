"""Tests for ``phronesis.providers.usage``."""

from __future__ import annotations

import dataclasses

import pytest

from phronesis.providers.usage import TokenUsage


class TestTokenUsage:
    def test_default_construction_has_all_none(self) -> None:
        usage = TokenUsage()

        assert usage.input_tokens is None
        assert usage.output_tokens is None
        assert usage.cache_read_tokens is None
        assert usage.cache_creation_tokens is None

    def test_full_construction_assigns_fields(self) -> None:
        usage = TokenUsage(
            input_tokens=10,
            output_tokens=20,
            cache_read_tokens=5,
            cache_creation_tokens=2,
        )

        assert usage.input_tokens == 10
        assert usage.output_tokens == 20
        assert usage.cache_read_tokens == 5
        assert usage.cache_creation_tokens == 2

    def test_is_frozen(self) -> None:
        usage = TokenUsage(input_tokens=10)

        with pytest.raises(dataclasses.FrozenInstanceError):
            usage.input_tokens = 99  # type: ignore[misc]

    def test_uses_slots(self) -> None:
        assert TokenUsage.__slots__ == (
            "input_tokens",
            "output_tokens",
            "cache_read_tokens",
            "cache_creation_tokens",
        )
        assert not hasattr(TokenUsage(), "__dict__")

    def test_equality(self) -> None:
        a = TokenUsage(input_tokens=1, output_tokens=2)
        b = TokenUsage(input_tokens=1, output_tokens=2)

        assert a == b
