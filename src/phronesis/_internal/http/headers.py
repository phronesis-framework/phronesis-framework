"""Default headers and redaction of sensitive header values."""

from __future__ import annotations

from collections.abc import Mapping
from typing import Final

_SENSITIVE_HEADERS: Final[frozenset[str]] = frozenset(
    {
        "authorization",
        "x-api-key",
        "api-key",
        "cookie",
        "set-cookie",
        "proxy-authorization",
    }
)

_REDACTED: Final[str] = "***"


def build_default_headers() -> dict[str, str]:
    """Return the default headers attached to every request (``User-Agent``)."""
    from phronesis import __version__

    return {"User-Agent": f"phronesis-framework/{__version__}"}


def redact_sensitive_headers(headers: Mapping[str, str]) -> dict[str, str]:
    """Return a copy of ``headers`` with sensitive values replaced by ``***``."""
    return {
        key: (_REDACTED if key.lower() in _SENSITIVE_HEADERS else value)
        for key, value in headers.items()
    }
