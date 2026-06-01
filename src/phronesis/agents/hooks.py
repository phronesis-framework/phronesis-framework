"""Callback-style hooks for the agent loop.

Hooks are user-supplied callables invoked at well-defined lifecycle
points during :func:`phronesis.agents.loop.run_loop` and
:func:`phronesis.agents.loop.run_loop_stream`. They are complementary
to the :class:`AgentEvent` stream exposed by :meth:`Agent.stream` —
events suit consumers that pull from an iterator, hooks suit
fire-and-forget side effects (logging, metrics, audit trails).

Every hook may be sync or async; the loop awaits the return value
when it is awaitable. Hook exceptions are caught and logged but do
**not** abort the run: hooks are observers, not policy.

Hooks are attached to an :class:`AgentSpec` via the
:class:`AgentHooks` aggregate. The decorator and the fluent
:meth:`Agent.with_hooks` helper accept an :class:`AgentHooks` value
directly.
"""

from __future__ import annotations

from collections.abc import Awaitable, Callable
from dataclasses import dataclass
from typing import TYPE_CHECKING, TypeAlias

if TYPE_CHECKING:
    from phronesis.agents.run import Result
    from phronesis.core.messages import ToolResultBlock, ToolUseBlock


IterationHook: TypeAlias = Callable[[int], Awaitable[None] | None]
"""Signature for hooks called on every loop iteration.

The single argument is the 1-based iteration number. Called after
the provider response has been received and budgeted but before any
tools are invoked.
"""

ToolCallHook: TypeAlias = Callable[
    ["ToolUseBlock", "ToolResultBlock"],
    Awaitable[None] | None,
]
"""Signature for hooks called after every tool invocation.

The hook receives the requested :class:`ToolUseBlock` and the
resulting :class:`ToolResultBlock` (which may carry ``is_error``).
"""

RunCompleteHook: TypeAlias = Callable[["Result"], Awaitable[None] | None]
"""Signature for hooks called once when a run finishes successfully."""


@dataclass(frozen=True, slots=True)
class AgentHooks:
    """Aggregate of optional callbacks attached to an agent.

    All fields default to ``None``. Construct with only the hooks you
    care about::

        hooks = AgentHooks(on_iteration=lambda i: print(f"step {i}"))

    Attributes:
        on_iteration: Called once per loop iteration with the 1-based
            iteration number.
        on_tool_call: Called after every tool invocation with the
            requested ``ToolUseBlock`` and the resulting
            ``ToolResultBlock``.
        on_run_complete: Called once when the run terminates with a
            ``Result``. Not called when the run aborts with an error.
    """

    on_iteration: IterationHook | None = None
    on_tool_call: ToolCallHook | None = None
    on_run_complete: RunCompleteHook | None = None


_EMPTY_HOOKS: AgentHooks = AgentHooks()
"""Singleton :class:`AgentHooks` with every field unset."""
