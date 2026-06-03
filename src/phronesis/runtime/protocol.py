"""Executable protocol: the single contract every runtime node honours.

Anything that can be orchestrated by the runtime layer ultimately satisfies
:class:`Executable`. Modes (``Sequence``, ``Parallel``, ``Retry``, ...) are
themselves ``Executable`` so they compose freely with one another, and with
agents or callables that have been adapted via :mod:`phronesis.runtime.node`.

The protocol is intentionally minimal: a single ``__call__`` that receives an
immutable :class:`ExecutionContext` plus a free-form input and returns a
normalised :class:`RunOutcome`.
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Any, Protocol, runtime_checkable

if TYPE_CHECKING:
    from phronesis.runtime.context import ExecutionContext
    from phronesis.runtime.outcome import RunOutcome


@runtime_checkable
class Executable(Protocol):
    """Single contract honoured by every runtime node.

    Implementations must be async-callable with ``(ctx, input)`` and return a
    :class:`RunOutcome`. They are expected to be stateless and idempotent
    with respect to their own dataclass fields; per-run state lives in
    ``ctx`` (which is itself immutable; callers derive children via
    :meth:`ExecutionContext.child`).
    """

    async def __call__(
        self, ctx: ExecutionContext, input: Any
    ) -> RunOutcome:  # pragma: no cover - protocol stub
        ...
