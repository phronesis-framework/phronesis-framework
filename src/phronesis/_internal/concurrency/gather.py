"""Concurrent execution of awaitables with configurable error policies."""

from __future__ import annotations

import asyncio
import time
from collections.abc import Awaitable
from typing import TypeVar, cast

from ..logging import get_logger
from .policies import FailFastPolicy, GatherPolicy

T = TypeVar("T")

_LOGGER_NAME = "phronesis.concurrency"


async def gather_all(
    *awaitables: Awaitable[T],
    policy: GatherPolicy | None = None,
) -> list[T]:
    """Run ``awaitables`` concurrently and reconcile via ``policy``.

    Args:
        *awaitables: Awaitables scheduled on the running event loop.
        policy: Error-handling strategy. Defaults to
            :class:`FailFastPolicy`. Use :class:`BestEffortPolicy` to
            wait for every task and surface partial failures.

    Returns:
        Results in input order. For :class:`BestEffortPolicy`, failed
        slots are replaced with ``None`` before the policy raises.

    Raises:
        Exception: The first exception raised by any awaitable under
            :class:`FailFastPolicy`.
        PartialFailureError: When :class:`BestEffortPolicy` finds at
            least one failed awaitable.
    """
    effective_policy = policy or FailFastPolicy()
    log = get_logger(_LOGGER_NAME)

    log.debug(
        "gather_all start",
        extra={
            "count": len(awaitables),
            "policy": type(effective_policy).__name__,
        },
    )

    started = time.perf_counter()

    raw = await asyncio.gather(
        *awaitables,
        return_exceptions=effective_policy.return_exceptions,
    )

    duration_ms = (time.perf_counter() - started) * 1000

    log.debug(
        "gather_all done",
        extra={"count": len(awaitables), "duration_ms": duration_ms},
    )

    return cast("list[T]", effective_policy.reconcile(raw))
