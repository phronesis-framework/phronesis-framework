"""Tests for :class:`Pricing`, the caller-supplied cost model."""

from __future__ import annotations

import pytest

from phronesis.providers.pricing import Pricing
from phronesis.providers.usage import TokenUsage


class TestEstimate:
    def test_zero_rates_cost_nothing(self) -> None:
        usage = TokenUsage(input_tokens=1_000_000, output_tokens=1_000_000)

        assert Pricing().estimate(usage) == 0.0

    def test_absent_counters_contribute_nothing(self) -> None:
        pricing = Pricing(input=3.0, output=15.0, cache_read=0.3, cache_write=3.75)

        assert pricing.estimate(TokenUsage()) == 0.0

    def test_input_and_output_are_priced_per_million(self) -> None:
        usage = TokenUsage(input_tokens=1_000_000, output_tokens=500_000)

        cost = Pricing(input=3.0, output=15.0).estimate(usage)

        assert cost == pytest.approx(3.0 + 7.5)

    def test_cache_counters_are_priced_independently(self) -> None:
        usage = TokenUsage(cache_read_tokens=2_000_000, cache_creation_tokens=1_000_000)

        cost = Pricing(cache_read=0.3, cache_write=3.75).estimate(usage)

        assert cost == pytest.approx(0.6 + 3.75)

    def test_a_zero_rate_excludes_a_counter_the_vendor_double_counts(self) -> None:
        usage = TokenUsage(input_tokens=1_000_000, cache_read_tokens=1_000_000)

        cost = Pricing(input=3.0, cache_read=0.0).estimate(usage)

        assert cost == pytest.approx(3.0)

    def test_partial_millions_scale_linearly(self) -> None:
        usage = TokenUsage(input_tokens=1_500, output_tokens=0)

        cost = Pricing(input=2.0).estimate(usage)

        assert cost == pytest.approx(0.003)
