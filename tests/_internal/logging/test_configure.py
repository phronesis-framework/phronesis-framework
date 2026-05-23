"""Tests for configure_logging."""

from __future__ import annotations

import io
import json
import logging

from phronesis._internal.logging import (
    PHRONESIS_LOGGER_PREFIX,
    HumanReadableFormatter,
    StructuredFormatter,
    configure_logging,
    get_logger,
)


def _root() -> logging.Logger:
    return logging.getLogger(PHRONESIS_LOGGER_PREFIX)


def _managed_handlers() -> list[logging.Handler]:
    return [h for h in _root().handlers if not isinstance(h, logging.NullHandler)]


class TestConfigureLogging:
    def teardown_method(self) -> None:
        # Strip handlers we installed so tests do not leak state.
        for handler in list(_root().handlers):
            if not isinstance(handler, logging.NullHandler):
                _root().removeHandler(handler)

    def test_installs_a_single_handler(self) -> None:
        configure_logging()
        assert len(_managed_handlers()) == 1

    def test_is_idempotent(self) -> None:
        configure_logging()
        configure_logging()
        assert len(_managed_handlers()) == 1

    def test_sets_root_level(self) -> None:
        configure_logging(level=logging.DEBUG)
        assert _root().level == logging.DEBUG

    def test_uses_structured_formatter_by_default(self) -> None:
        configure_logging()
        assert isinstance(_managed_handlers()[0].formatter, StructuredFormatter)

    def test_uses_human_readable_formatter_when_requested(self) -> None:
        configure_logging(structured=False)
        assert isinstance(_managed_handlers()[0].formatter, HumanReadableFormatter)

    def test_writes_to_provided_stream(self) -> None:
        stream = io.StringIO()
        configure_logging(level=logging.INFO, stream=stream)
        get_logger("phronesis.test.configure").info("hello")
        parsed = json.loads(stream.getvalue())
        assert parsed["message"] == "hello"
        assert parsed["logger"] == "phronesis.test.configure"
