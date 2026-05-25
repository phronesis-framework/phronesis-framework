"""Provider error hierarchy.

A small, actionable hierarchy under :class:`ProviderError`. Each
subclass maps to a category of failure that callers may want to handle
differently: authentication, rate limiting, context overflow, server
faults, malformed requests, transport problems and streaming errors.

:class:`RateLimitError` exposes :attr:`retry_after_seconds` so the retry
layer can honor server-provided backoff hints via ``delay_hook``.
"""

from __future__ import annotations


class ProviderError(Exception):
    """Base class for all provider errors."""


class TransportError(ProviderError):
    """Network failure: timeout, connection reset, DNS error, etc."""


class AuthenticationError(ProviderError):
    """Missing or invalid credentials (typically 401/403)."""


class RateLimitError(ProviderError):
    """Rate limit or quota exceeded (typically 429).

    ``retry_after_seconds`` is set when the provider returns a
    ``Retry-After`` header or an equivalent hint.
    """

    def __init__(
        self,
        message: str = "",
        *,
        retry_after_seconds: float | None = None,
    ) -> None:
        super().__init__(message)

        self.retry_after_seconds = retry_after_seconds


class ContextWindowExceededError(ProviderError):
    """Input exceeds the model's context window."""


class ServerError(ProviderError):
    """5xx response from the provider."""


class BadRequestError(ProviderError):
    """4xx response not covered by a more specific subclass."""


class StreamError(ProviderError):
    """Failure during streaming: dropped connection, malformed event, etc."""
