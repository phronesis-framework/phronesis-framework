"""Tests for HttpClient request/response behavior using httpx.MockTransport."""

from __future__ import annotations

import json

import httpx
import pytest

from phronesis import __version__
from phronesis._internal.http import (
    HttpClient,
    HttpClientError,
    HttpConnectionError,
    HttpServerError,
    HttpTimeoutError,
    HttpTimeouts,
    configure_http_client,
)


def _ok_handler(request: httpx.Request) -> httpx.Response:
    return httpx.Response(
        200,
        headers={"content-type": "application/json"},
        content=json.dumps({"ok": True, "method": request.method}).encode(),
    )


def _status_handler(status: int, body: bytes = b"{}") -> httpx.MockTransport:
    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(status, content=body, headers={"content-type": "application/json"})

    return httpx.MockTransport(handler)


def _client(transport: httpx.MockTransport) -> HttpClient:
    return HttpClient(base_url="https://example.test", transport=transport)


class TestRequestSuccess:
    async def test_get_returns_2xx_response(self) -> None:
        async with _client(httpx.MockTransport(_ok_handler)) as c:
            r = await c.get("/x")
        assert r.status_code == 200
        assert r.json() == {"ok": True, "method": "GET"}
        assert r.duration_ms >= 0.0

    async def test_post_with_json(self) -> None:
        captured: dict[str, object] = {}

        def handler(request: httpx.Request) -> httpx.Response:
            captured["body"] = request.content
            return httpx.Response(201, content=b'{"created": true}')

        async with _client(httpx.MockTransport(handler)) as c:
            r = await c.post("/x", json={"a": 1})
        assert r.status_code == 201
        assert json.loads(captured["body"]) == {"a": 1}  # type: ignore[arg-type]

    async def test_put_patch_delete_dispatch_method(self) -> None:
        async with _client(httpx.MockTransport(_ok_handler)) as c:
            assert (await c.put("/x")).json()["method"] == "PUT"
            assert (await c.patch("/x")).json()["method"] == "PATCH"
            assert (await c.delete("/x")).json()["method"] == "DELETE"

    async def test_default_user_agent_is_sent(self) -> None:
        seen: dict[str, str] = {}

        def handler(request: httpx.Request) -> httpx.Response:
            seen["ua"] = request.headers.get("user-agent", "")
            return httpx.Response(200)

        async with _client(httpx.MockTransport(handler)) as c:
            await c.get("/x")
        assert seen["ua"] == f"phronesis-framework/{__version__}"

    async def test_caller_headers_override_defaults(self) -> None:
        seen: dict[str, str] = {}

        def handler(request: httpx.Request) -> httpx.Response:
            seen["ua"] = request.headers.get("user-agent", "")
            return httpx.Response(200)

        async with _client(httpx.MockTransport(handler)) as c:
            await c.get("/x", headers={"User-Agent": "custom/1.0"})
        assert seen["ua"] == "custom/1.0"


class TestResponseErrors:
    async def test_4xx_raises_client_error_with_response(self) -> None:
        async with _client(_status_handler(404, b'{"err":"x"}')) as c:
            with pytest.raises(HttpClientError) as info:
                await c.get("/x")
        assert info.value.status_code == 404
        assert info.value.response.json() == {"err": "x"}
        assert info.value.request.method == "GET"

    async def test_5xx_raises_server_error_with_response(self) -> None:
        async with _client(_status_handler(503, b'{"err":"down"}')) as c:
            with pytest.raises(HttpServerError) as info:
                await c.get("/x")
        assert info.value.status_code == 503
        assert info.value.response.json() == {"err": "down"}


class TestTransportErrors:
    async def test_timeout_raises_timeout_error(self) -> None:
        def handler(request: httpx.Request) -> httpx.Response:
            raise httpx.ReadTimeout("read timed out", request=request)

        async with _client(httpx.MockTransport(handler)) as c:
            with pytest.raises(HttpTimeoutError) as info:
                await c.get("/x")
        assert isinstance(info.value.cause, httpx.ReadTimeout)
        assert info.value.request.method == "GET"

    async def test_connect_error_raises_connection_error(self) -> None:
        def handler(request: httpx.Request) -> httpx.Response:
            raise httpx.ConnectError("dns failure", request=request)

        async with _client(httpx.MockTransport(handler)) as c:
            with pytest.raises(HttpConnectionError) as info:
                await c.get("/x")
        assert isinstance(info.value.cause, httpx.ConnectError)


class TestTimeoutsConfiguration:
    async def test_custom_timeouts_passed_to_httpx(self) -> None:
        t = HttpTimeouts(connect=2.0, read=5.0, write=2.0, pool=1.0)
        c = HttpClient(base_url="https://x", timeouts=t)
        try:
            assert c._httpx.timeout.connect == 2.0
            assert c._httpx.timeout.read == 5.0
        finally:
            await c.close()

    async def test_per_request_timeout_overrides_client(self) -> None:
        seen_timeout: dict[str, object] = {}

        def handler(request: httpx.Request) -> httpx.Response:
            seen_timeout["extensions"] = request.extensions.get("timeout")
            return httpx.Response(200)

        async with _client(httpx.MockTransport(handler)) as c:
            await c.get("/x", timeouts=HttpTimeouts(read=99.0))
        ext = seen_timeout["extensions"]
        assert ext is not None
        assert ext["read"] == 99.0  # type: ignore[index]


class TestResourceManagement:
    async def test_close_then_request_raises_clear_error(self) -> None:
        c = HttpClient(base_url="https://x", transport=httpx.MockTransport(_ok_handler))
        await c.close()
        with pytest.raises(RuntimeError):
            await c.get("/x")


class TestConfigureHttpClient:
    async def test_returns_http_client(self) -> None:
        c = configure_http_client(base_url="https://x")
        try:
            assert isinstance(c, HttpClient)
        finally:
            await c.close()
