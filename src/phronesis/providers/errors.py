"""Provider error hierarchy.

A small, actionable hierarchy rooted at :class:`ProviderError`. Each
subclass maps to a category of failure that callers may want to
handle differently: authentication, rate limiting, context overflow,
server faults, malformed requests, transport problems and streaming
errors. The retry layer reads :attr:`RateLimitError.retry_after_seconds`
to honour server-provided backoff hints.
"""

from __future__ import annotations


class ProviderError(Exception):
    """Base class for all provider errors.

    Provider adapters raise a subclass; callers can catch the base
    when they want to handle "any provider failure" uniformly.
    """


class TransportError(ProviderError):
    """Network-layer failure before a response was received.

    Covers timeouts, connection resets, DNS errors and similar
    conditions where the request never reached a usable answer.
    """


class AuthenticationError(ProviderError):
    """Missing or invalid credentials.

    Typically corresponds to a 401 or 403 HTTP status.
    """


class RateLimitError(ProviderError):
    """Rate limit or quota exceeded.

    Typically corresponds to a 429 HTTP status. The optional
    :attr:`retry_after_seconds` value is forwarded to the retry layer
    so callers can defer to the server's hint instead of computing
    a local backoff.

    Attributes:
        retry_after_seconds: Suggested delay in seconds before
            retrying. ``None`` when the provider did not include the
            hint.
    """

    def __init__(
        self,
        message: str = "",
        *,
        retry_after_seconds: float | None = None,
    ) -> None:
        """Build a rate-limit error.

        Args:
            message: Human-readable description.
            retry_after_seconds: Optional backoff hint extracted
                from the provider response.
        """
        super().__init__(message)

        self.retry_after_seconds = retry_after_seconds


class ContextWindowExceededError(ProviderError):
    """Input exceeds the model's context window.

    Raised when the provider reports that the prompt plus expected
    output would not fit in the configured model's context.
    """


class ServerError(ProviderError):
    """Provider-side fault.

    Typically corresponds to a 5xx HTTP status; safe to retry.
    """


class BadRequestError(ProviderError):
    """Malformed request rejected by the provider.

    Typically corresponds to a 4xx HTTP status not covered by a
    more specific subclass.
    """


class StreamError(ProviderError):
    """Failure during streaming.

    Covers dropped connections mid-stream, malformed server-sent
    events, and other faults that occur after the first chunk has
    been received.
    """
