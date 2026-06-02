"""Optional setup/teardown lifecycle for tools.

Tools occasionally need to acquire a resource (database connection,
HTTP session, file handle) before being invoked and release it when
the agent run finishes. The :class:`ToolLifecycle` aggregate carries
those two callbacks; the agent loop invokes them once per run via
:func:`run_tools_lifecycle`.

Both callbacks are optional and may be sync or async. When the loop
finishes - successfully or via an exception - every ``teardown`` is
invoked exactly once, even when the run aborted. Exceptions raised
by ``teardown`` are caught and logged so a misbehaving tool cannot
mask the run's outcome.
"""

from __future__ import annotations

from collections.abc import Awaitable, Callable
from dataclasses import dataclass
from typing import TypeAlias

SetupFn: TypeAlias = Callable[[], Awaitable[None] | None]
"""Signature for tool ``setup`` callbacks."""

TeardownFn: TypeAlias = Callable[[], Awaitable[None] | None]
"""Signature for tool ``teardown`` callbacks."""


@dataclass(frozen=True, slots=True)
class ToolLifecycle:
    """Aggregate of optional ``setup``/``teardown`` callbacks.

    Attributes:
        setup: Optional callable executed once at the start of every
            agent run that uses the tool. Invoked **before** any of
            the tool's calls.
        teardown: Optional callable executed once at the end of every
            agent run. Invoked from a ``finally`` block so it always
            runs, regardless of how the run terminated.
    """

    setup: SetupFn | None = None
    teardown: TeardownFn | None = None


NO_LIFECYCLE: ToolLifecycle = ToolLifecycle()
"""Singleton :class:`ToolLifecycle` with both fields unset."""
