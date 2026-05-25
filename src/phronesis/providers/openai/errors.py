"""HTTP error translation for the OpenAI provider.

Maps OpenAI's JSON error envelope and HTTP status to the framework's
:mod:`phronesis.providers.errors` hierarchy, preserving the original
message and ``retry-after`` hint when present.
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

_CONTEXT_LENGTH_CODES = frozenset(
    {"context_length_exceeded", "string_above_max_length"},
)
_CONTEXT_LENGTH_HINTS = ("context length", "maximum context", "context_length")


def translate_response_error(response: httpx.Response) -> ProviderError:
    """Convert a 4xx/5xx :class:`httpx.Response` into a :class:`ProviderError`."""
    payload = _safe_json(response)
    error = payload.get("error") if isinstance(payload, dict) else None
    err_dict = error if isinstance(error, dict) else {}
    message = str(err_dict.get("message") or response.reason_phrase or "OpenAI error")
    error_type = str(err_dict.get("type") or "")
    error_code = str(err_dict.get("code") or "")
    status = response.status_code

    if status in (401, 403):
        return AuthenticationError(message)

    if status == 429:
        return RateLimitError(
            message,
            retry_after_seconds=_parse_retry_after(response.headers.get("retry-after")),
        )

    if status == 400:
        if _is_context_length(error_code, message):
            return ContextWindowExceededError(message)

        return BadRequestError(message)

    if status >= 500 or error_type == "server_error":
        return ServerError(message)

    return BadRequestError(message)


def _safe_json(response: httpx.Response) -> Any:
    try:
        return response.json()
    except ValueError:
        return None


def _parse_retry_after(value: str | None) -> float | None:
    if value is None:
        return None

    try:
        return float(value)
    except ValueError:
        return None


def _is_context_length(code: str, message: str) -> bool:
    if code in _CONTEXT_LENGTH_CODES:
        return True

    lowered = message.lower()

    return any(hint in lowered for hint in _CONTEXT_LENGTH_HINTS)
