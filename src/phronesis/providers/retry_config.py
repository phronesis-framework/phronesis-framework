"""Retry configuration for provider network calls.

:class:`RetryConfig` is the user-facing knob set; provider adapters
turn an instance into a decorator via :func:`build_retry_decorator`
and wrap their network operations with it.

Defaults retry the transient categories every provider can hit:
:class:`TransportError`, :class:`RateLimitError` and
:class:`ServerError`. When ``honor_retry_after`` is ``True`` (the
default) the retry layer reads
:attr:`RateLimitError.retry_after_seconds` and uses it in place of
the configured backoff.
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
        max_attempts: Maximum number of attempts, inclusive of the
            first.
        on: Exception types eligible for retry. Anything not in this
            tuple propagates immediately.
        backoff: Backoff strategy. ``None`` falls back to the retry
            layer's default (exponential backoff with jitter).
        honor_retry_after: When ``True``, any ``retry_after_seconds``
            attribute on the raised exception overrides the backoff
            delay for that attempt.
        should_retry: Optional predicate that returns ``True`` to
            keep an exception eligible for retry. Useful to filter
            within a broad exception type (e.g. retry only a subset
            of :class:`ServerError`).
    """

    max_attempts: int = 3
    on: tuple[type[BaseException], ...] = field(default_factory=lambda: _DEFAULT_RETRYABLE)
    backoff: BackoffStrategy | None = None
    honor_retry_after: bool = True
    should_retry: Callable[[Exception], bool] | None = None


def build_retry_decorator(
    config: RetryConfig,
) -> Callable[[Callable[P, Awaitable[T]]], Callable[P, Awaitable[T]]]:
    """Return a :func:`retry` decorator configured from ``config``.

    Args:
        config: The :class:`RetryConfig` whose fields parameterise
            the resulting decorator.

    Returns:
        A decorator that, when applied to an awaitable function,
        wraps each call with the retry policy expressed by
        ``config``.
    """
    return retry(
        on=config.on,
        max_attempts=config.max_attempts,
        should_retry=config.should_retry,
        backoff=config.backoff,
        honor_retry_after=config.honor_retry_after,
    )
