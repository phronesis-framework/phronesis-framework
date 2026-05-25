"""Error-handling policies for concurrent task execution."""

from __future__ import annotations

from abc import ABC, abstractmethod
from collections.abc import Sequence
from typing import Any

from .exceptions import PartialFailureError


class GatherPolicy(ABC):
    """Strategy for handling exceptions returned by :func:`asyncio.gather`."""

    @property
    @abstractmethod
    def return_exceptions(self) -> bool:
        """Value passed to ``asyncio.gather(return_exceptions=...)``."""

    @abstractmethod
    def reconcile(self, results: Sequence[Any]) -> list[Any]:
        """Inspect raw gather output and either return successes or raise."""


class FailFastPolicy(GatherPolicy):
    """Cancel pending tasks and propagate the first exception immediately."""

    @property
    def return_exceptions(self) -> bool:
        return False

    def reconcile(self, results: Sequence[Any]) -> list[Any]:
        # With return_exceptions=False, asyncio.gather already raised on
        # the first failure, so any sequence we receive is all-successful.
        return list(results)


class BestEffortPolicy(GatherPolicy):
    """Wait for every task; raise :class:`PartialFailureError` if any failed."""

    @property
    def return_exceptions(self) -> bool:
        return True

    def reconcile(self, results: Sequence[Any]) -> list[Any]:
        successes: list[Any] = []
        failures: list[BaseException | None] = []
        any_failed = False

        for item in results:
            if isinstance(item, BaseException):
                successes.append(None)
                failures.append(item)
                any_failed = True

            else:
                successes.append(item)
                failures.append(None)

        if any_failed:
            failed = sum(1 for exc in failures if exc is not None)
            total = len(results)

            raise PartialFailureError(
                f"{failed} of {total} tasks failed",
                results=successes,
                exceptions=failures,
            )

        return successes
