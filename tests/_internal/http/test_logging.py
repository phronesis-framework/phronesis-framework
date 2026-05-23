"""Tests for HTTP request/response logging and header redaction."""

from __future__ import annotations

import io
import json
import logging

import httpx

from phronesis._internal.http import HttpClient
from phronesis._internal.logging import (
    PHRONESIS_LOGGER_PREFIX,
    StructuredFormatter,
)


def _ok(request: httpx.Request) -> httpx.Response:
    return httpx.Response(200, content=b"{}", headers={"content-type": "application/json"})


def _install_capture_handler(stream: io.StringIO) -> logging.Handler:
    handler = logging.StreamHandler(stream)
    handler.setFormatter(StructuredFormatter())
    handler.setLevel(logging.DEBUG)
    root = logging.getLogger(PHRONESIS_LOGGER_PREFIX)
    root.addHandler(handler)
    root.setLevel(logging.DEBUG)
    return handler


def _remove_handler(handler: logging.Handler) -> None:
    logging.getLogger(PHRONESIS_LOGGER_PREFIX).removeHandler(handler)


class TestHttpLogging:
    async def test_logs_method_url_and_status(self) -> None:
        stream = io.StringIO()
        handler = _install_capture_handler(stream)
        try:
            async with HttpClient(
                base_url="https://example.test",
                transport=httpx.MockTransport(_ok),
            ) as c:
                await c.get("/x")
        finally:
            _remove_handler(handler)

        lines = [json.loads(line) for line in stream.getvalue().splitlines() if line.strip()]
        request_logs = [line for line in lines if line["message"] == "http request"]
        response_logs = [line for line in lines if line["message"] == "http response"]
        assert request_logs and request_logs[0]["method"] == "GET"
        assert response_logs and response_logs[0]["status_code"] == 200
        assert "duration_ms" in response_logs[0]

    async def test_redacts_sensitive_headers_in_logs(self) -> None:
        stream = io.StringIO()
        handler = _install_capture_handler(stream)
        try:
            async with HttpClient(
                base_url="https://example.test",
                transport=httpx.MockTransport(_ok),
            ) as c:
                await c.get("/x", headers={"Authorization": "Bearer s3cr3t", "X-API-Key": "k"})
        finally:
            _remove_handler(handler)

        # Every line that contains the headers must show *** rather than the secret.
        text = stream.getvalue()
        assert "s3cr3t" not in text
        assert "***" in text

    async def test_silent_when_no_handler_installed(self, capsys) -> None:  # type: ignore[no-untyped-def]
        # NullHandler is installed at import time in src/phronesis/__init__.py,
        # so no records should be emitted to stderr/stdout by default.
        async with HttpClient(
            base_url="https://example.test",
            transport=httpx.MockTransport(_ok),
        ) as c:
            await c.get("/x")
        captured = capsys.readouterr()
        assert captured.out == ""
        assert captured.err == ""
