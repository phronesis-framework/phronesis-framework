"""Async HTTP client wrapping :class:`httpx.AsyncClient`."""

from __future__ import annotations

import time
from collections.abc import AsyncIterator, Mapping
from types import TracebackType
from typing import Any, Self

import httpx

from ..logging import get_logger
from .exceptions import (
    HttpClientError,
    HttpConnectionError,
    HttpServerError,
    HttpTimeoutError,
)
from .headers import build_default_headers, redact_sensitive_headers
from .models import HttpRequest, HttpResponse
from .timeouts import HttpTimeouts

_LOGGER_NAME = "phronesis.http"


def _to_request(request: httpx.Request) -> HttpRequest:
    return HttpRequest(
        method=request.method,
        url=str(request.url),
        headers=dict(request.headers),
        content=bytes(request.content) if request.content else None,
    )


def _to_response(response: httpx.Response, *, duration_ms: float) -> HttpResponse:
    return HttpResponse(
        status_code=response.status_code,
        headers=dict(response.headers),
        content=response.content,
        text=response.text,
        duration_ms=duration_ms,
    )


def _raise_for_status(response: HttpResponse, request: HttpRequest) -> None:
    if response.status_code < 400:
        return

    message = f"HTTP {response.status_code} for {request.method} {request.url}"

    if response.status_code < 500:
        raise HttpClientError(
            message,
            status_code=response.status_code,
            response=response,
            request=request,
        )

    raise HttpServerError(
        message,
        status_code=response.status_code,
        response=response,
        request=request,
    )


class HttpStreamResponse:
    """Streaming view over an in-flight 2xx HTTP response."""

    def __init__(self, response: httpx.Response, *, duration_ms: float) -> None:
        self._response = response
        self._duration_ms = duration_ms

    @property
    def status_code(self) -> int:
        return self._response.status_code

    @property
    def headers(self) -> Mapping[str, str]:
        return dict(self._response.headers)

    @property
    def duration_ms(self) -> float:
        return self._duration_ms

    def iter_bytes(self) -> AsyncIterator[bytes]:
        return self._response.aiter_bytes()

    def iter_text(self) -> AsyncIterator[str]:
        return self._response.aiter_text()

    def iter_lines(self) -> AsyncIterator[str]:
        return self._response.aiter_lines()


class _StreamContext:
    """Async context manager returned by :meth:`HttpClient.stream`."""

    def __init__(
        self,
        client: HttpClient,
        method: str,
        url: str,
        *,
        json: Any = None,
        content: bytes | None = None,
        params: Mapping[str, Any] | None = None,
        headers: Mapping[str, str] | None = None,
        timeouts: HttpTimeouts | None = None,
    ) -> None:
        self._client = client
        self._method = method
        self._url = url
        self._json = json
        self._content = content
        self._params = params
        self._headers = headers
        self._timeouts = timeouts

        self._ctx: Any = None
        self._stream: HttpStreamResponse | None = None
        self._started: float = 0.0

    async def __aenter__(self) -> HttpStreamResponse:
        kwargs: dict[str, Any] = {}

        if self._json is not None:
            kwargs["json"] = self._json

        if self._content is not None:
            kwargs["content"] = self._content

        if self._params is not None:
            kwargs["params"] = self._params

        if self._headers is not None:
            kwargs["headers"] = dict(self._headers)

        if self._timeouts is not None:
            kwargs["timeout"] = self._timeouts.to_httpx()

        self._started = time.perf_counter()
        self._ctx = self._client._httpx.stream(self._method, self._url, **kwargs)

        try:
            response = await self._ctx.__aenter__()

        except httpx.TimeoutException as exc:
            req = HttpRequest(method=self._method, url=self._url, headers={}, content=None)
            raise HttpTimeoutError(str(exc) or "request timed out", request=req, cause=exc) from exc

        except (httpx.ConnectError, httpx.NetworkError) as exc:
            req = HttpRequest(method=self._method, url=self._url, headers={}, content=None)
            raise HttpConnectionError(
                str(exc) or "connection failed", request=req, cause=exc
            ) from exc

        if response.status_code >= 400:
            await response.aread()

            duration_ms = (time.perf_counter() - self._started) * 1000
            req = _to_request(response.request)
            resp = _to_response(response, duration_ms=duration_ms)

            await self._ctx.__aexit__(None, None, None)
            self._ctx = None

            _raise_for_status(resp, req)

        duration_ms = (time.perf_counter() - self._started) * 1000
        self._stream = HttpStreamResponse(response, duration_ms=duration_ms)

        self._client._log.debug(
            "http stream opened",
            extra={
                "method": self._method,
                "url": self._url,
                "status_code": response.status_code,
                "duration_ms": duration_ms,
            },
        )

        return self._stream

    async def __aexit__(
        self,
        exc_type: type[BaseException] | None,
        exc: BaseException | None,
        tb: TracebackType | None,
    ) -> None:
        if self._ctx is not None:
            await self._ctx.__aexit__(exc_type, exc, tb)
            self._ctx = None


class HttpClient:
    """Async HTTP client used by every provider via composition.

    Wraps :class:`httpx.AsyncClient` with framework-owned response/error types,
    per-phase timeouts, and structured logging. Use as an async context manager
    or call :meth:`close` explicitly.
    """

    def __init__(
        self,
        *,
        base_url: str = "",
        timeouts: HttpTimeouts | None = None,
        headers: Mapping[str, str] | None = None,
        transport: httpx.AsyncBaseTransport | None = None,
    ) -> None:
        merged_headers = build_default_headers()

        if headers:
            merged_headers.update(headers)

        self._timeouts = timeouts or HttpTimeouts()

        self._httpx = httpx.AsyncClient(
            base_url=base_url,
            timeout=self._timeouts.to_httpx(),
            headers=merged_headers,
            transport=transport,
        )

        self._log = get_logger(_LOGGER_NAME)

    async def __aenter__(self) -> Self:
        return self

    async def __aexit__(
        self,
        exc_type: type[BaseException] | None,
        exc: BaseException | None,
        tb: TracebackType | None,
    ) -> None:
        await self.close()

    async def close(self) -> None:
        """Release the underlying connection pool."""
        await self._httpx.aclose()

    async def request(
        self,
        method: str,
        url: str,
        *,
        json: Any = None,
        content: bytes | None = None,
        params: Mapping[str, Any] | None = None,
        headers: Mapping[str, str] | None = None,
        timeouts: HttpTimeouts | None = None,
    ) -> HttpResponse:
        """Send an HTTP request and return the parsed :class:`HttpResponse`.

        Raises :class:`HttpClientError` for 4xx, :class:`HttpServerError` for
        5xx, :class:`HttpTimeoutError` on timeout, and
        :class:`HttpConnectionError` for transport failures.
        """
        kwargs: dict[str, Any] = {}

        if json is not None:
            kwargs["json"] = json

        if content is not None:
            kwargs["content"] = content

        if params is not None:
            kwargs["params"] = params

        if headers is not None:
            kwargs["headers"] = dict(headers)

        if timeouts is not None:
            kwargs["timeout"] = timeouts.to_httpx()

        self._log.debug(
            "http request",
            extra={
                "method": method,
                "url": url,
                "headers": redact_sensitive_headers(kwargs.get("headers", {})),
                "body_size": len(content) if content else 0,
            },
        )

        started = time.perf_counter()

        try:
            response = await self._httpx.request(method, url, **kwargs)

        except httpx.TimeoutException as exc:
            req = HttpRequest(method=method, url=url, headers={}, content=None)

            self._log.warning(
                "http timeout",
                extra={"method": method, "url": url, "error": str(exc)},
            )

            raise HttpTimeoutError(str(exc) or "request timed out", request=req, cause=exc) from exc

        except (httpx.ConnectError, httpx.NetworkError) as exc:
            req = HttpRequest(method=method, url=url, headers={}, content=None)

            self._log.warning(
                "http connection failure",
                extra={"method": method, "url": url, "error": str(exc)},
            )

            raise HttpConnectionError(
                str(exc) or "connection failed", request=req, cause=exc
            ) from exc

        duration_ms = (time.perf_counter() - started) * 1000

        framework_request = _to_request(response.request)
        framework_response = _to_response(response, duration_ms=duration_ms)

        self._log.debug(
            "http response",
            extra={
                "method": method,
                "url": url,
                "status_code": framework_response.status_code,
                "duration_ms": duration_ms,
                "body_size": len(framework_response.content),
            },
        )

        _raise_for_status(framework_response, framework_request)

        return framework_response

    async def get(self, url: str, **kwargs: Any) -> HttpResponse:
        return await self.request("GET", url, **kwargs)

    async def post(self, url: str, **kwargs: Any) -> HttpResponse:
        return await self.request("POST", url, **kwargs)

    async def put(self, url: str, **kwargs: Any) -> HttpResponse:
        return await self.request("PUT", url, **kwargs)

    async def patch(self, url: str, **kwargs: Any) -> HttpResponse:
        return await self.request("PATCH", url, **kwargs)

    async def delete(self, url: str, **kwargs: Any) -> HttpResponse:
        return await self.request("DELETE", url, **kwargs)

    def stream(
        self,
        method: str,
        url: str,
        *,
        json: Any = None,
        content: bytes | None = None,
        params: Mapping[str, Any] | None = None,
        headers: Mapping[str, str] | None = None,
        timeouts: HttpTimeouts | None = None,
    ) -> _StreamContext:
        """Open a streaming request.

        Returns an async context manager that yields :class:`HttpStreamResponse`.
        For 4xx/5xx responses the body is read in full and the appropriate
        :class:`HttpResponseError` is raised on ``__aenter__``.
        """
        return _StreamContext(
            self,
            method,
            url,
            json=json,
            content=content,
            params=params,
            headers=headers,
            timeouts=timeouts,
        )


def configure_http_client(
    *,
    base_url: str = "",
    timeouts: HttpTimeouts | None = None,
    headers: Mapping[str, str] | None = None,
) -> HttpClient:
    """Construct an :class:`HttpClient` with framework defaults."""
    return HttpClient(base_url=base_url, timeouts=timeouts, headers=headers)
