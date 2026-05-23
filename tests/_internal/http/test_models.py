"""Tests for HttpRequest and HttpResponse."""

from __future__ import annotations

from phronesis._internal.http import HttpRequest, HttpResponse


class TestHttpRequest:
    def test_holds_method_url_headers_and_content(self) -> None:
        r = HttpRequest(
            method="POST",
            url="https://example.com/x",
            headers={"User-Agent": "p"},
            content=b"{}",
        )
        assert r.method == "POST"
        assert r.url == "https://example.com/x"
        assert r.headers["User-Agent"] == "p"
        assert r.content == b"{}"


class TestHttpResponse:
    def test_holds_response_fields(self) -> None:
        r = HttpResponse(
            status_code=200,
            headers={"content-type": "application/json"},
            content=b'{"ok": true}',
            text='{"ok": true}',
            duration_ms=12.5,
        )
        assert r.status_code == 200
        assert r.duration_ms == 12.5

    def test_json_decodes_content(self) -> None:
        r = HttpResponse(
            status_code=200,
            headers={},
            content=b'{"a": 1}',
            text='{"a": 1}',
            duration_ms=0.0,
        )
        assert r.json() == {"a": 1}
