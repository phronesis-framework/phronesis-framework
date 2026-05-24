"""Tests for ``Budget``."""

from __future__ import annotations

from dataclasses import FrozenInstanceError

import pytest

from phronesis.context import Budget


class TestBudgetDefaults:
    def test_all_fields_default_to_none(self) -> None:
        budget = Budget()

        assert budget.tokens_remaining is None
        assert budget.cost_remaining_usd is None


class TestBudgetConstruction:
    def test_accepts_tokens_remaining(self) -> None:
        budget = Budget(tokens_remaining=1000)

        assert budget.tokens_remaining == 1000
        assert budget.cost_remaining_usd is None

    def test_accepts_cost_remaining_usd(self) -> None:
        budget = Budget(cost_remaining_usd=2.5)

        assert budget.cost_remaining_usd == 2.5
        assert budget.tokens_remaining is None

    def test_accepts_both_fields(self) -> None:
        budget = Budget(tokens_remaining=500, cost_remaining_usd=1.0)

        assert budget.tokens_remaining == 500
        assert budget.cost_remaining_usd == 1.0


class TestBudgetImmutability:
    def test_cannot_assign_to_tokens_remaining(self) -> None:
        budget = Budget(tokens_remaining=10)

        with pytest.raises(FrozenInstanceError):
            budget.tokens_remaining = 99  # type: ignore[misc]

    def test_cannot_assign_to_cost_remaining_usd(self) -> None:
        budget = Budget(cost_remaining_usd=1.0)

        with pytest.raises(FrozenInstanceError):
            budget.cost_remaining_usd = 99.0  # type: ignore[misc]


class TestBudgetEquality:
    def test_two_budgets_with_same_fields_are_equal(self) -> None:
        a = Budget(tokens_remaining=10, cost_remaining_usd=1.0)
        b = Budget(tokens_remaining=10, cost_remaining_usd=1.0)

        assert a == b

    def test_two_budgets_with_different_fields_are_not_equal(self) -> None:
        a = Budget(tokens_remaining=10)
        b = Budget(tokens_remaining=20)

        assert a != b
