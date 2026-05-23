"""Run synchronous callables from async code via a worker thread."""

from __future__ import annotations

import asyncio
import time
from collections.abc import Callable
from typing import ParamSpec, TypeVar

from ..logging import get_logger

P = ParamSpec("P")
T = TypeVar("T")

_LOGGER_NAME = "phronesis.concurrency"


async def run_sync(
    fn: Callable[P, T],
    *args: P.args,
    **kwargs: P.kwargs,
) -> T:
    """Run a synchronous callable in a worker thread.

    Wraps :func:`asyncio.to_thread` with structured logging. The callable
    runs in the default executor and exceptions propagate unchanged.
    """
    log = get_logger(_LOGGER_NAME)
    label = getattr(fn, "__qualname__", repr(fn))

    log.debug("run_sync start", extra={"callable": label})

    started = time.perf_counter()

    try:
        result = await asyncio.to_thread(fn, *args, **kwargs)

    except Exception as exc:
        duration_ms = (time.perf_counter() - started) * 1000

        log.warning(
            "run_sync failed",
            extra={
                "callable": label,
                "duration_ms": duration_ms,
                "error": str(exc),
            },
        )

        raise

    duration_ms = (time.perf_counter() - started) * 1000

    log.debug(
        "run_sync done",
        extra={"callable": label, "duration_ms": duration_ms},
    )

    return result
