"""Exception hierarchy for the HTTP client."""

from __future__ import annotations

from .models import HttpRequest, HttpResponse


class HttpError(Exception):
    """Base class for every error raised by :class:`HttpClient`."""


class HttpResponseError(HttpError):
    """HTTP error response (status >= 400) with the full response attached."""

    def __init__(
        self,
        message: str,
        *,
        status_code: int,
        response: HttpResponse,
        request: HttpRequest,
    ) -> None:
        super().__init__(message)
        self.message = message
        self.status_code = status_code
        self.response = response
        self.request = request


class HttpClientError(HttpResponseError):
    """Client-side response error (status 4xx)."""


class HttpServerError(HttpResponseError):
    """Server-side response error (status 5xx)."""


class HttpTransportError(HttpError):
    """Transport-level failure (no response received)."""

    def __init__(
        self,
        message: str,
        *,
        request: HttpRequest,
        cause: Exception,
    ) -> None:
        super().__init__(message)
        self.message = message
        self.request = request
        self.cause = cause


class HttpTimeoutError(HttpTransportError):
    """Connect/read/write/pool timeout."""


class HttpConnectionError(HttpTransportError):
    """DNS, refused, reset, or other connection-level failures."""
