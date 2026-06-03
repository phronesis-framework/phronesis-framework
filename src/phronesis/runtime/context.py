"""Run-scoped execution context.

An :class:`ExecutionContext` is the only mutable handle a node receives
on the current run. The dataclass itself is frozen; mutation happens via
:meth:`ExecutionContext.child`, which returns a derived context with a
fresh :class:`RunId` and the parent id wired in.

The context carries:

* a unique :class:`RunId` and optional ``parent_id`` (composition graph),
* an optional monotonic ``deadline`` (wall-clock cap for the whole tree),
* an :class:`asyncio.Event` for cooperative cancellation,
* a read-only ``metadata`` mapping,
* a :class:`logging.Logger` for narration.

Nothing else: no agent registry, no provider, no memory store. Modes that
need extra dependencies receive them through their own dataclass fields.
"""

from __future__ import annotations

import asyncio
import logging
import time
from collections.abc import Mapping
from dataclasses import dataclass
from types import MappingProxyType
from typing import Any, Final

from phronesis._internal.ids.generator import IdGenerator
from phronesis._internal.ids.id import Id

_EMPTY_METADATA: Final[Mapping[str, Any]] = MappingProxyType({})


class RunId(Id):
    """Stable identifier for one runtime execution.

    Distinct from :class:`phronesis.agents.run.RunId` because the runtime
    composition graph is independent of the agent loop's own run ids.
    """

    prefix = "RTID"


run_id_generator: IdGenerator[RunId] = IdGenerator(RunId)
"""Process-wide :class:`IdGenerator` bound to runtime :class:`RunId`."""


def _new_run_id() -> RunId:
    canonical = f"phronesis.runtime.run.r{id(object()):x}"

    return run_id_generator.from_canonical(canonical)


@dataclass(frozen=True, slots=True)
class ExecutionContext:
    """Immutable per-run handle threaded through every node call.

    Attributes:
        run_id: Identifier of this node's execution.
        parent_id: Identifier of the parent context, or ``None`` for the root.
        deadline: Monotonic seconds (``time.monotonic`` units) past which
            modes should refuse to start new work. ``None`` disables the
            check.
        cancellation: Event signalling cooperative cancellation. Long
            running modes poll :meth:`is_cancelled` between iterations.
        metadata: Read-only free-form mapping. Coerced to
            :class:`MappingProxyType` so callers cannot mutate it.
        logger: Logger used by modes that need to narrate decisions.
    """

    run_id: RunId
    parent_id: RunId | None
    deadline: float | None
    cancellation: asyncio.Event
    metadata: Mapping[str, Any]
    logger: logging.Logger

    def __post_init__(self) -> None:
        if not isinstance(self.metadata, MappingProxyType):
            object.__setattr__(self, "metadata", MappingProxyType(dict(self.metadata)))

    @classmethod
    def new(
        cls,
        *,
        deadline_s: float | None = None,
        metadata: Mapping[str, Any] | None = None,
        logger: logging.Logger | None = None,
    ) -> ExecutionContext:
        """Build a fresh root context.

        Args:
            deadline_s: Wall-clock cap for the whole run in seconds. The
                stored ``deadline`` is computed as
                ``time.monotonic() + deadline_s``. ``None`` disables it.
            metadata: Initial metadata mapping. Copied defensively.
            logger: Logger to attach. Defaults to ``phronesis.runtime``.
        """
        deadline = None if deadline_s is None else time.monotonic() + deadline_s

        return cls(
            run_id=_new_run_id(),
            parent_id=None,
            deadline=deadline,
            cancellation=asyncio.Event(),
            metadata=metadata if metadata is not None else _EMPTY_METADATA,
            logger=logger if logger is not None else logging.getLogger("phronesis.runtime"),
        )

    def child(
        self,
        *,
        metadata: Mapping[str, Any] | None = None,
    ) -> ExecutionContext:
        """Derive a child context.

        The child inherits ``deadline``, ``cancellation`` (shared, so a
        cancel at the root cancels descendants) and ``logger``. Its
        ``parent_id`` is set to this context's ``run_id``.

        Args:
            metadata: Replacement metadata mapping. ``None`` keeps the
                parent's metadata.
        """
        return ExecutionContext(
            run_id=_new_run_id(),
            parent_id=self.run_id,
            deadline=self.deadline,
            cancellation=self.cancellation,
            metadata=metadata if metadata is not None else self.metadata,
            logger=self.logger,
        )

    def remaining(self) -> float | None:
        """Seconds until the deadline, or ``None`` when no deadline is set.

        May return a negative number; callers decide whether to honour or
        ignore an overrun.
        """
        if self.deadline is None:
            return None

        return self.deadline - time.monotonic()

    def is_cancelled(self) -> bool:
        """Return ``True`` once :meth:`cancel` has been invoked."""
        return self.cancellation.is_set()

    def cancel(self) -> None:
        """Signal cooperative cancellation to every node sharing this context."""
        self.cancellation.set()
