"""Tests for ContextLoggerAdapter."""

from __future__ import annotations

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
    logger = logging.getLogger("phronesis.test.adapter")
    logger.setLevel(logging.DEBUG)
    logger.propagate = False
    handler = CapturingHandler()
    logger.addHandler(handler)
    try:
        yield logger, handler
    finally:
        logger.removeHandler(handler)


class TestContextLoggerAdapter:
    def test_context_fields_attached_to_record(
        self, isolated_logger: tuple[logging.Logger, CapturingHandler]
    ) -> None:
        logger, handler = isolated_logger
        adapter = ContextLoggerAdapter(logger, {"run_id": "r1", "agent_id": "a1"})
        adapter.info("hello")
        assert handler.records[0].run_id == "r1"  # type: ignore[attr-defined]
        assert handler.records[0].agent_id == "a1"  # type: ignore[attr-defined]

    def test_call_site_extras_merge_with_context(
        self, isolated_logger: tuple[logging.Logger, CapturingHandler]
    ) -> None:
        logger, handler = isolated_logger
        adapter = ContextLoggerAdapter(logger, {"run_id": "r1"})
        adapter.info("hello", extra={"duration_ms": 42})
        rec = handler.records[0]
        assert rec.run_id == "r1"  # type: ignore[attr-defined]
        assert rec.duration_ms == 42  # type: ignore[attr-defined]

    def test_call_site_overrides_context_on_conflict(
        self, isolated_logger: tuple[logging.Logger, CapturingHandler]
    ) -> None:
        logger, handler = isolated_logger
        adapter = ContextLoggerAdapter(logger, {"run_id": "r1"})
        adapter.info("hello", extra={"run_id": "override"})
        assert handler.records[0].run_id == "override"  # type: ignore[attr-defined]

    def test_separate_adapters_do_not_share_context(
        self, isolated_logger: tuple[logging.Logger, CapturingHandler]
    ) -> None:
        logger, handler = isolated_logger
        a = ContextLoggerAdapter(logger, {"agent_id": "A"})
        b = ContextLoggerAdapter(logger, {"agent_id": "B"})
        a.info("from a")
        b.info("from b")
        assert handler.records[0].agent_id == "A"  # type: ignore[attr-defined]
        assert handler.records[1].agent_id == "B"  # type: ignore[attr-defined]
