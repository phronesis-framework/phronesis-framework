"""Tests for :class:`CachePolicy` and :class:`ToolCache`."""

from __future__ import annotations

import time
from collections.abc import Iterator

import pytest

from phronesis.tools.cache import NO_CACHE, CachePolicy, ToolCache, make_cache_key


class TestCachePolicyDefaults:
    def test_default_policy_is_enabled(self) -> None:
        assert CachePolicy().enabled

    def test_no_cache_is_disabled(self) -> None:
        assert not NO_CACHE.enabled

    def test_negative_size_is_clamped_to_zero(self) -> None:
        policy = CachePolicy(max_size=-3)

        assert policy.max_size == 0
        assert not policy.enabled

    def test_negative_ttl_is_clamped_to_zero(self) -> None:
        policy = CachePolicy(ttl_seconds=-1.0)

        assert policy.ttl_seconds == 0.0

    def test_policy_is_frozen(self) -> None:
        policy = CachePolicy()

        with pytest.raises(AttributeError):
            policy.max_size = 999  # type: ignore[misc]


class TestMakeCacheKey:
    def test_key_is_order_insensitive(self) -> None:
        assert make_cache_key({"a": 1, "b": 2}) == make_cache_key({"b": 2, "a": 1})

    def test_distinct_args_produce_distinct_keys(self) -> None:
        assert make_cache_key({"a": 1}) != make_cache_key({"a": 2})

    def test_non_json_value_falls_back_to_repr(self) -> None:
        class _NotJson:
            def __repr__(self) -> str:
                return "<custom>"

        key = make_cache_key({"x": _NotJson()})

        assert "custom" in key


class TestToolCacheBehavior:
    def test_get_on_missing_key_is_miss(self) -> None:
        cache = ToolCache(CachePolicy(max_size=2))

        hit, value = cache.get("nope")

        assert hit is False
        assert value is None

    def test_set_then_get_is_hit(self) -> None:
        cache = ToolCache(CachePolicy(max_size=2))

        cache.set("k", 42)
        hit, value = cache.get("k")

        assert hit is True
        assert value == 42

    def test_disabled_policy_stores_nothing(self) -> None:
        cache = ToolCache(NO_CACHE)

        cache.set("k", 42)

        assert len(cache) == 0
        hit, _ = cache.get("k")

        assert hit is False

    def test_lru_evicts_oldest_entry(self) -> None:
        cache = ToolCache(CachePolicy(max_size=2))

        cache.set("a", 1)
        cache.set("b", 2)
        cache.set("c", 3)

        assert len(cache) == 2
        assert cache.get("a") == (False, None)
        assert cache.get("b") == (True, 2)
        assert cache.get("c") == (True, 3)

    def test_get_refreshes_recency(self) -> None:
        cache = ToolCache(CachePolicy(max_size=2))

        cache.set("a", 1)
        cache.set("b", 2)
        cache.get("a")
        cache.set("c", 3)

        assert cache.get("a") == (True, 1)
        assert cache.get("b") == (False, None)
        assert cache.get("c") == (True, 3)

    def test_ttl_expires_entries(self, monkeypatch: pytest.MonkeyPatch) -> None:
        clock: Iterator[float] = iter([100.0, 105.0])
        monkeypatch.setattr(time, "monotonic", lambda: next(clock))

        cache = ToolCache(CachePolicy(max_size=2, ttl_seconds=1.0))
        cache.set("k", "v")
        hit, _ = cache.get("k")

        assert hit is False
        assert len(cache) == 0

    def test_clear_empties_the_cache(self) -> None:
        cache = ToolCache(CachePolicy(max_size=2))
        cache.set("a", 1)
        cache.set("b", 2)

        cache.clear()

        assert len(cache) == 0
        assert cache.get("a") == (False, None)
