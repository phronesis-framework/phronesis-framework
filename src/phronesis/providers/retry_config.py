"""Retry configuration for provider network calls.

Providers wrap their HTTP operations with
:func:`phronesis._internal.retry.retry`. This module exposes a
:class:`RetryConfig` dataclass with sensible defaults and a helper that
turns it into a ready-to-use decorator.

By default, :class:`TransportError`, :class:`RateLimitError` and
:class:`ServerError` are retried. ``RateLimitError.retry_after_seconds``
is honored automatically by the retry layer via ``honor_retry_after``.
"""

from __future__ import annotations

from collections.abc import Awaitable, Callable
from dataclasses import dataclass, field
from typing import ParamSpec, TypeVar

from phronesis._internal.retry import BackoffStrategy, retry
from phronesis.providers.errors import RateLimitError, ServerError, TransportError

P = ParamSpec("P")
T = TypeVar("T")

_DEFAULT_RETRYABLE: tuple[type[BaseException], ...] = (
    TransportError,
    RateLimitError,
    ServerError,
)


@dataclass(frozen=True, slots=True)
class RetryConfig:
    """Configuration for retrying a provider's network operations.

    Attributes:
        max_attempts: Maximum number of attempts (inclusive of the first).
        on: Exception types eligible for retry.
        backoff: Backoff strategy. ``None`` falls back to the retry layer's
            default (:class:`ExponentialBackoff` with jitter).
        honor_retry_after: When ``True``, ``retry_after_seconds`` on the
            raised exception overrides the backoff delay.
        should_retry: Optional predicate to filter retryable exceptions
            (e.g. ignore certain ``ServerError`` subclasses).
    """

    max_attempts: int = 3
    on: tuple[type[BaseException], ...] = field(default_factory=lambda: _DEFAULT_RETRYABLE)
    backoff: BackoffStrategy | None = None
    honor_retry_after: bool = True
    should_retry: Callable[[Exception], bool] | None = None


def build_retry_decorator(
    config: RetryConfig,
) -> Callable[[Callable[P, Awaitable[T]]], Callable[P, Awaitable[T]]]:
    """Return a :func:`retry` decorator configured from ``config``."""
    return retry(
        on=config.on,
        max_attempts=config.max_attempts,
        should_retry=config.should_retry,
        backoff=config.backoff,
        honor_retry_after=config.honor_retry_after,
    )
