"""Concurrency tests: parallel async contexts must not contaminate each other."""

from __future__ import annotations

import asyncio
import logging
from collections.abc import Iterator

import pytest

from phronesis._internal.logging import ContextLoggerAdapter


class CapturingHandler(logging.Handler):
    def __init__(self) -> None:
        super().__init__()

        self.records: list[logging.LogRecord] = []

    def emit(self, record: logging.LogRecord) -> None:
        self.records.append(record)


@pytest.fixture
def isolated_logger() -> Iterator[tuple[logging.Logger, CapturingHandler]]:
    logger = logging.getLogger("phronesis.test.concurrency")
    logger.setLevel(logging.DEBUG)
    logger.propagate = False

    handler = CapturingHandler()
    logger.addHandler(handler)

    try:
        yield logger, handler

    finally:
        logger.removeHandler(handler)


class TestConcurrency:
    def test_parallel_contexts_do_not_mix(
        self, isolated_logger: tuple[logging.Logger, CapturingHandler]
    ) -> None:
        logger, handler = isolated_logger

        async def worker(run_id: str, ticks: int) -> None:
            adapter = ContextLoggerAdapter(logger, {"run_id": run_id})

            for _ in range(ticks):
                adapter.info("tick")
                await asyncio.sleep(0)

        async def main() -> None:
            await asyncio.gather(
                worker("A", 5),
                worker("B", 5),
                worker("C", 5),
            )

        asyncio.run(main())

        counts: dict[str, int] = {}

        for rec in handler.records:
            run_id: str = rec.run_id  # type: ignore[attr-defined]
            counts[run_id] = counts.get(run_id, 0) + 1

        assert counts == {"A": 5, "B": 5, "C": 5}
