"""Map Anthropic HTTP responses to the provider error hierarchy.

Anthropic error responses come as JSON of the form
``{"type": "error", "error": {"type": ..., "message": ...}}`` along
with an HTTP status. This module inspects both and builds the
appropriate :class:`ProviderError` subclass, preserving the original
human-readable message and extracting the ``Retry-After`` header
when the failure is a rate-limit.
"""

from __future__ import annotations

from typing import Any

import httpx

from phronesis.providers.errors import (
    AuthenticationError,
    BadRequestError,
    ContextWindowExceededError,
    ProviderError,
    RateLimitError,
    ServerError,
)

_CONTEXT_LENGTH_HINTS = (
    "context length",
    "maximum context",
    "context window",
    "prompt is too long",
)


def _extract_error_details(response: httpx.Response) -> tuple[str, str]:
    try:
        payload: Any = response.json()
    except ValueError:
        return "", response.text or ""

    if not isinstance(payload, dict):
        return "", response.text or ""

    error = payload.get("error")

    if not isinstance(error, dict):
        return "", str(payload)

    raw_type = error.get("type", "")
    raw_message = error.get("message", "")
    error_type = raw_type if isinstance(raw_type, str) else ""
    message = raw_message if isinstance(raw_message, str) else ""

    return error_type, message


def _parse_retry_after(response: httpx.Response) -> float | None:
    raw = response.headers.get("retry-after")

    if raw is None:
        return None

    try:
        return float(raw)
    except ValueError:
        return None


def _classify(status: int, error_type: str, message: str) -> type[ProviderError]:
    if status in (401, 403):
        return AuthenticationError

    if status == 429:
        return RateLimitError

    if status == 400:
        lowered = message.lower()

        if any(hint in lowered for hint in _CONTEXT_LENGTH_HINTS):
            return ContextWindowExceededError

        return BadRequestError

    if status >= 500 or error_type in {"overloaded_error", "api_error"}:
        return ServerError

    return BadRequestError


def translate_response_error(response: httpx.Response) -> ProviderError:
    """Build the appropriate :class:`ProviderError` for an HTTP error response.

    The classification looks at the HTTP status first, then at the
    vendor-specific ``error.type`` and message for the few cases the
    status alone cannot disambiguate (most notably 400s caused by
    context-window overflow).

    Args:
        response: The :class:`httpx.Response` whose status indicates
            a failure (``>= 400``).

    Returns:
        A concrete :class:`ProviderError` subclass instance carrying
        the failure message and, for rate-limit errors, the parsed
        ``Retry-After`` value.
    """
    error_type, message = _extract_error_details(response)
    text = message or response.reason_phrase or f"HTTP {response.status_code}"
    error_cls = _classify(response.status_code, error_type, message)

    if error_cls is RateLimitError:
        return RateLimitError(text, retry_after_seconds=_parse_retry_after(response))

    return error_cls(text)
