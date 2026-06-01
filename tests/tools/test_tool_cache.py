"""Integration tests for caching on :class:`Tool`."""

from __future__ import annotations

import asyncio

import pytest

from phronesis.context.context import Context
from phronesis.tools.cache import CachePolicy
from phronesis.tools.decorator import tool
from phronesis.tools.registry import tool_scope

_CALLS: list[int] = []


def _square(x: int) -> int:
    _CALLS.append(x)
    return x * x


def _square_uncached(x: int) -> int:
    _CALLS.append(x)
    return x * x


def _flaky(x: int) -> int:
    _CALLS.append(x)
    raise RuntimeError("nope")


def _with_ctx(x: int, ctx: Context) -> str:
    _CALLS.append(x)
    return f"{x}/{ctx.trace_id}"


async def _double(x: int) -> int:
    _CALLS.append(x)
    return x * 2


def _echo(x: int) -> int:
    _CALLS.append(x)
    return x


class TestSyncCaching:
    def setup_method(self) -> None:
        _CALLS.clear()

    def test_repeated_calls_with_same_args_hit_cache(self) -> None:
        with tool_scope():
            wrapped = tool(id="phronesis.tools.tests.square", cache=CachePolicy(max_size=8))(
                _square
            )

            assert wrapped.invoke({"x": 3}) == 9
            assert wrapped.invoke({"x": 3}) == 9
            assert wrapped.invoke({"x": 4}) == 16
            assert wrapped.invoke({"x": 3}) == 9

        assert _CALLS == [3, 4]

    def test_no_cache_recomputes_every_call(self) -> None:
        with tool_scope():
            wrapped = tool(id="phronesis.tools.tests.square_uncached")(_square_uncached)

            wrapped.invoke({"x": 3})
            wrapped.invoke({"x": 3})

        assert _CALLS == [3, 3]

    def test_clear_cache_forces_recompute(self) -> None:
        with tool_scope():
            wrapped = tool(
                id="phronesis.tools.tests.square_clear",
                cache=CachePolicy(max_size=8),
            )(_square)

            wrapped.invoke({"x": 2})
            wrapped.clear_cache()
            wrapped.invoke({"x": 2})

        assert _CALLS == [2, 2]

    def test_exceptions_are_not_cached(self) -> None:
        with tool_scope():
            wrapped = tool(
                id="phronesis.tools.tests.flaky",
                cache=CachePolicy(max_size=4),
            )(_flaky)

            with pytest.raises(RuntimeError):
                wrapped.invoke({"x": 1})

            with pytest.raises(RuntimeError):
                wrapped.invoke({"x": 1})

        assert _CALLS == [1, 1]

    def test_context_is_not_part_of_cache_key(self) -> None:
        with tool_scope():
            wrapped = tool(
                id="phronesis.tools.tests.with_ctx",
                cache=CachePolicy(max_size=4),
            )(_with_ctx)

            first = wrapped.invoke({"x": 1}, context=Context(trace_id="t-1"))
            second = wrapped.invoke({"x": 1}, context=Context(trace_id="t-2"))

        assert _CALLS == [1]
        assert first == "1/t-1"
        assert second == "1/t-1"


class TestAsyncCaching:
    def setup_method(self) -> None:
        _CALLS.clear()

    def test_async_tool_uses_cache(self) -> None:
        with tool_scope():
            wrapped = tool(
                id="phronesis.tools.tests.double",
                cache=CachePolicy(max_size=4),
            )(_double)

            first = asyncio.run(wrapped.invoke({"x": 5}))
            second = asyncio.run(wrapped.invoke({"x": 5}))

        assert first == 10
        assert second == 10
        assert _CALLS == [5]


class TestDisabledCache:
    def setup_method(self) -> None:
        _CALLS.clear()

    def test_explicit_disabled_policy_skips_cache(self) -> None:
        with tool_scope():
            wrapped = tool(
                id="phronesis.tools.tests.echo",
                cache=CachePolicy(max_size=0),
            )(_echo)

            wrapped.invoke({"x": 1})
            wrapped.invoke({"x": 1})

        assert _CALLS == [1, 1]
