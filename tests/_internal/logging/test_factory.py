"""Tests for get_logger and get_logger_with_context."""

from __future__ import annotations

import logging

from phronesis._internal.logging import (
    ContextLoggerAdapter,
    get_logger,
    get_logger_with_context,
)


class TestGetLogger:
    def test_returns_logger_with_given_name(self) -> None:
        logger = get_logger("phronesis.test.factory.one")
        assert isinstance(logger, logging.Logger)
        assert logger.name == "phronesis.test.factory.one"

    def test_same_name_returns_same_instance(self) -> None:
        a = get_logger("phronesis.test.factory.two")
        b = get_logger("phronesis.test.factory.two")
        assert a is b


class TestGetLoggerWithContext:
    def test_returns_context_adapter(self) -> None:
        adapter = get_logger_with_context("phronesis.test.factory.ctx", run_id="r1")
        assert isinstance(adapter, ContextLoggerAdapter)

    def test_context_baked_into_adapter(self) -> None:
        adapter = get_logger_with_context("phronesis.test.factory.ctx2", run_id="r1", agent_id="a1")
        assert adapter.extra == {"run_id": "r1", "agent_id": "a1"}

    def test_wraps_correct_underlying_logger(self) -> None:
        adapter = get_logger_with_context("phronesis.test.factory.ctx3")
        assert adapter.logger.name == "phronesis.test.factory.ctx3"
