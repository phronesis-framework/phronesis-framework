"""Tests for HttpClient streaming behavior."""

from __future__ import annotations

from collections.abc import Callable

import httpx
import pytest

from phronesis._internal.http import (
    HttpClient,
    HttpClientError,
    HttpServerError,
)


def _make_client(handler: Callable[[httpx.Request], httpx.Response]) -> HttpClient:
    return HttpClient(base_url="https://example.test", transport=httpx.MockTransport(handler))


class TestStreamSuccess:
    async def test_2xx_yields_chunks(self) -> None:
        def handler(request: httpx.Request) -> httpx.Response:
            return httpx.Response(200, content=b"chunk-1chunk-2")

        async with _make_client(handler) as c, c.stream("GET", "/x") as stream:
            assert stream.status_code == 200

            collected = b""
            async for chunk in stream.iter_bytes():
                collected += chunk

        assert collected == b"chunk-1chunk-2"

    async def test_iter_lines(self) -> None:
        def handler(request: httpx.Request) -> httpx.Response:
            return httpx.Response(200, content=b"line-1\nline-2\n")

        async with _make_client(handler) as c, c.stream("GET", "/x") as stream:
            lines = [line async for line in stream.iter_lines()]

        assert "line-1" in lines
        assert "line-2" in lines


class TestStreamErrors:
    async def test_4xx_reads_body_and_raises_client_error(self) -> None:
        def handler(request: httpx.Request) -> httpx.Response:
            return httpx.Response(400, content=b'{"err":"bad"}')

        async with _make_client(handler) as c:
            with pytest.raises(HttpClientError) as info:
                async with c.stream("POST", "/x") as _:
                    pytest.fail("should not enter stream body")

        assert info.value.status_code == 400
        assert info.value.response.json() == {"err": "bad"}

    async def test_5xx_reads_body_and_raises_server_error(self) -> None:
        def handler(request: httpx.Request) -> httpx.Response:
            return httpx.Response(500, content=b'{"err":"down"}')

        async with _make_client(handler) as c:
            with pytest.raises(HttpServerError) as info:
                async with c.stream("GET", "/x") as _:
                    pytest.fail("should not enter stream body")

        assert info.value.status_code == 500
