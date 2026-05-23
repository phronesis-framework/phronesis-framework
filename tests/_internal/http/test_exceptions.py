"""Tests for the exception hierarchy."""

from __future__ import annotations

import pytest

from phronesis._internal.http import (
    HttpClientError,
    HttpConnectionError,
    HttpError,
    HttpRequest,
    HttpResponse,
    HttpResponseError,
    HttpServerError,
    HttpTimeoutError,
    HttpTransportError,
)


def _req() -> HttpRequest:
    return HttpRequest(method="GET", url="https://x", headers={}, content=None)


def _resp(status: int = 400) -> HttpResponse:
    return HttpResponse(
        status_code=status,
        headers={},
        content=b"",
        text="",
        duration_ms=0.0,
    )


class TestHierarchy:
    def test_client_error_is_response_error(self) -> None:
        assert issubclass(HttpClientError, HttpResponseError)
        assert issubclass(HttpResponseError, HttpError)

    def test_server_error_is_response_error(self) -> None:
        assert issubclass(HttpServerError, HttpResponseError)

    def test_timeout_is_transport_error(self) -> None:
        assert issubclass(HttpTimeoutError, HttpTransportError)
        assert issubclass(HttpTransportError, HttpError)

    def test_connection_is_transport_error(self) -> None:
        assert issubclass(HttpConnectionError, HttpTransportError)


class TestResponseErrorAttributes:
    def test_holds_status_response_and_request(self) -> None:
        req = _req()
        resp = _resp(404)
        with pytest.raises(HttpClientError) as info:
            raise HttpClientError("not found", status_code=404, response=resp, request=req)
        assert info.value.status_code == 404
        assert info.value.response is resp
        assert info.value.request is req
        assert info.value.message == "not found"


class TestTransportErrorAttributes:
    def test_holds_request_and_cause(self) -> None:
        req = _req()
        cause = RuntimeError("boom")
        with pytest.raises(HttpTimeoutError) as info:
            raise HttpTimeoutError("timed out", request=req, cause=cause)
        assert info.value.request is req
        assert info.value.cause is cause
        assert info.value.message == "timed out"
