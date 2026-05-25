"""Tests for run_sync."""

from __future__ import annotations

import threading

import pytest

from phronesis._internal.concurrency import run_sync


class TestRunSync:
    async def test_returns_value_from_sync_callable(self) -> None:
        def add(a: int, b: int) -> int:
            return a + b

        result = await run_sync(add, 2, 3)

        assert result == 5

    async def test_passes_kwargs(self) -> None:
        def greet(name: str, *, greeting: str = "hi") -> str:
            return f"{greeting} {name}"

        result = await run_sync(greet, "ada", greeting="hello")

        assert result == "hello ada"

    async def test_runs_in_a_worker_thread(self) -> None:
        main_thread = threading.get_ident()

        def worker() -> int:
            return threading.get_ident()

        worker_thread = await run_sync(worker)

        assert worker_thread != main_thread

    async def test_propagates_exceptions(self) -> None:
        def boom() -> None:
            raise ValueError("kaboom")

        with pytest.raises(ValueError, match="kaboom"):
            await run_sync(boom)

    async def test_returns_none_when_callable_returns_none(self) -> None:
        def noop() -> None:
            return None

        result = await run_sync(noop)

        assert result is None
