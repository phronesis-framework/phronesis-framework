"""``@with_retries`` decorator for async callables."""

from __future__ import annotations

import asyncio
import functools
import logging
import time
from collections.abc import Awaitable, Callable
from typing import ParamSpec, TypeVar

from ..logging import get_logger
from .attempt import AttemptInfo
from .backoff import BackoffStrategy, ExponentialBackoff
from .exceptions import RetryExhaustedError

P = ParamSpec("P")
T = TypeVar("T")

_LOGGER_NAME = "phronesis.retry"


def _calculate_delay(
    exc: Exception,
    attempt: int,
    backoff: BackoffStrategy,
    honor_retry_after: bool,
    delay_hook: Callable[[Exception], float | None] | None,
) -> float:
    """Pick the delay before the next attempt.

    Priority: ``delay_hook`` > ``retry_after_seconds`` (if honored) > ``backoff``.
    """
    if delay_hook is not None:
        hooked = delay_hook(exc)
        if hooked is not None:
            return hooked
    if honor_retry_after:
        retry_after = getattr(exc, "retry_after_seconds", None)
        if retry_after is not None:
            return float(retry_after)
    return backoff.get_delay(attempt)


def with_retries(
    *,
    retry_on: tuple[type[BaseException], ...],
    max_attempts: int = 3,
    should_retry: Callable[[Exception], bool] | None = None,
    backoff: BackoffStrategy | None = None,
    honor_retry_after: bool = True,
    delay_hook: Callable[[Exception], float | None] | None = None,
    log_level: int = logging.INFO,
) -> Callable[[Callable[P, Awaitable[T]]], Callable[P, Awaitable[T]]]:
    """Wrap an async callable so it is retried on transient failures.

    Raises :class:`RetryExhaustedError` (with the full attempt history) when
    ``max_attempts`` is reached. Exceptions outside ``retry_on`` are propagated
    immediately, as are exceptions for which ``should_retry`` returns ``False``.
    """
    effective_backoff: BackoffStrategy = backoff if backoff is not None else ExponentialBackoff()
    log = get_logger(_LOGGER_NAME)

    def decorator(fn: Callable[P, Awaitable[T]]) -> Callable[P, Awaitable[T]]:
        @functools.wraps(fn)
        async def wrapper(*args: P.args, **kwargs: P.kwargs) -> T:
            history: list[AttemptInfo] = []
            started = time.perf_counter()
            attempt = 1
            while True:
                attempt_started = time.perf_counter()
                try:
                    return await fn(*args, **kwargs)
                except Exception as exc:
                    attempt_duration_ms = (time.perf_counter() - attempt_started) * 1000
                    if not isinstance(exc, retry_on):
                        raise
                    if should_retry is not None and not should_retry(exc):
                        raise
                    if attempt >= max_attempts:
                        history.append(
                            AttemptInfo(
                                attempt_number=attempt,
                                exception=exc,
                                duration_ms=attempt_duration_ms,
                                delay_before_next_ms=None,
                            )
                        )
                        total_ms = (time.perf_counter() - started) * 1000
                        log.error(
                            "retries exhausted",
                            extra={
                                "attempts": attempt,
                                "total_duration_ms": total_ms,
                                "error": str(exc),
                            },
                        )
                        raise RetryExhaustedError(
                            attempts=attempt,
                            total_duration_ms=total_ms,
                            last_exception=exc,
                            attempt_history=history,
                        ) from exc

                    delay = _calculate_delay(
                        exc, attempt, effective_backoff, honor_retry_after, delay_hook
                    )
                    history.append(
                        AttemptInfo(
                            attempt_number=attempt,
                            exception=exc,
                            duration_ms=attempt_duration_ms,
                            delay_before_next_ms=delay * 1000,
                        )
                    )
                    log.log(
                        log_level,
                        "retrying",
                        extra={
                            "attempt": attempt,
                            "next_attempt": attempt + 1,
                            "delay_seconds": delay,
                            "error": str(exc),
                        },
                    )
                    await asyncio.sleep(delay)
                    attempt += 1

        return wrapper

    return decorator
