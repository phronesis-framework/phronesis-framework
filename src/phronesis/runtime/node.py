"""Adapters that turn agents or callables into :class:`Executable` nodes.

The runtime only knows about the :class:`Executable` protocol. Anything
else needs an adapter:

* :func:`agent_node` wraps a :class:`phronesis.agents.Agent` and translates
  its :class:`phronesis.agents.Result` into a :class:`RunOutcome`. The
  adapter is what makes an agent obey the run-scoped budget: it clamps
  the request's timeout to ``ctx.remaining()``, aborts the in-flight run
  when ``ctx`` is cancelled, and surfaces every ``AgentError`` as a
  failed outcome instead of letting it escape the graph.
* :func:`callable_node` wraps a coroutine function that takes either
  ``(ctx, input)`` or just ``(input)``. The adapter inspects the signature
  once at registration time.
* :func:`as_node` dispatches to one of the two based on the argument type.
"""

from __future__ import annotations

import asyncio
import dataclasses
import inspect
from collections.abc import Awaitable, Callable
from contextlib import suppress
from typing import TYPE_CHECKING, Any

from phronesis.runtime.errors import CancelledError
from phronesis.runtime.outcome import RunOutcome
from phronesis.runtime.protocol import Executable

if TYPE_CHECKING:
    from phronesis.agents import Agent
    from phronesis.agents.run import Result, RunRequest
    from phronesis.runtime.context import ExecutionContext


class _AgentNode:
    """Adapter from :class:`Agent` to :class:`Executable`."""

    __slots__ = ("_agent",)

    def __init__(self, agent: Agent) -> None:
        self._agent = agent

    async def __call__(self, ctx: ExecutionContext, input: Any) -> RunOutcome:
        from phronesis.agents.errors import AgentError
        from phronesis.agents.run import RunRequest

        if ctx.is_cancelled():
            return RunOutcome.fail(error=CancelledError("agent cancelled before start"))

        request = input if isinstance(input, RunRequest) else RunRequest(input=str(input))

        try:
            result = await _run_until_cancelled(self._agent, _bounded_by(request, ctx), ctx)
        except AgentError as exc:
            return RunOutcome.fail(error=exc)

        if result is None:
            return RunOutcome.fail(error=CancelledError("agent cancelled mid-run"))

        if result.success:
            return RunOutcome.ok(
                output=result.output,
                tokens=result.tokens,
                cost_usd=result.cost_usd,
            )

        error = result.error if result.error is not None else Exception("agent run failed")

        return RunOutcome.fail(
            error=error,
            output=result.output,
            tokens=result.tokens,
            cost_usd=result.cost_usd,
        )


async def _run_until_cancelled(
    agent: Agent,
    request: RunRequest,
    ctx: ExecutionContext,
) -> Result | None:
    """Run ``agent`` racing it against ``ctx``'s cancellation event.

    Returns the :class:`Result` when the run wins the race, or ``None``
    when cancellation does. In the latter case the run task is
    cancelled so the in-flight provider call is torn down instead of
    being left to finish unobserved.

    Raises:
        AgentError: whatever the loop raised, when the run lost to
            neither cancellation nor success.
    """
    run_task = asyncio.ensure_future(agent.run(request))
    cancel_task = asyncio.ensure_future(ctx.cancellation.wait())

    try:
        await asyncio.wait((run_task, cancel_task), return_when=asyncio.FIRST_COMPLETED)
    finally:
        cancel_task.cancel()

        with suppress(asyncio.CancelledError):
            await cancel_task

    if run_task.done():
        return run_task.result()

    run_task.cancel()

    with suppress(asyncio.CancelledError):
        await run_task

    return None


def _bounded_by(request: RunRequest, ctx: ExecutionContext) -> RunRequest:
    """Clamp ``request``'s timeout to the context's remaining deadline.

    The runtime owns the wall-clock budget of the whole graph; an agent
    must not outlive it. When the request already carries a tighter
    timeout the stricter of the two wins.
    """
    remaining = ctx.remaining()

    if remaining is None:
        return request

    if request.timeout_seconds is not None:
        remaining = min(remaining, request.timeout_seconds)

    return dataclasses.replace(request, timeout_seconds=max(remaining, 0.0))


class _CallableNode:
    """Adapter from an async callable to :class:`Executable`."""

    __slots__ = ("_fn", "_name", "_takes_ctx")

    def __init__(self, fn: Callable[..., Awaitable[Any]], *, name: str | None = None) -> None:
        self._fn = fn
        self._takes_ctx = _takes_two_positional(fn)
        self._name = name or getattr(fn, "__name__", "callable_node")

    async def __call__(self, ctx: ExecutionContext, input: Any) -> RunOutcome:
        try:
            output = await (self._fn(ctx, input) if self._takes_ctx else self._fn(input))
        except Exception as exc:
            return RunOutcome.fail(error=exc)

        if isinstance(output, RunOutcome):
            return output

        return RunOutcome.ok(output=output)


def _takes_two_positional(fn: Callable[..., Any]) -> bool:
    """Return ``True`` when ``fn`` accepts at least two positional args."""
    try:
        sig = inspect.signature(fn)
    except (TypeError, ValueError):
        return False

    positional = [
        p
        for p in sig.parameters.values()
        if p.kind
        in (
            inspect.Parameter.POSITIONAL_ONLY,
            inspect.Parameter.POSITIONAL_OR_KEYWORD,
        )
    ]

    return len(positional) >= 2


def agent_node(agent: Agent) -> Executable:
    """Wrap an :class:`Agent` so it satisfies :class:`Executable`."""
    return _AgentNode(agent)


def callable_node(
    fn: Callable[..., Awaitable[Any]],
    *,
    name: str | None = None,
) -> Executable:
    """Wrap an async callable so it satisfies :class:`Executable`.

    Accepts either ``async def f(ctx, input)`` or ``async def f(input)``.
    The wrapper inspects ``fn``'s signature once and caches the choice.

    Args:
        fn: Coroutine function to adapt.
        name: Optional display name preserved for diagnostics.
    """
    return _CallableNode(fn, name=name)


def as_node(target: Any) -> Executable:
    """Dispatch to :func:`agent_node` or :func:`callable_node`.

    Anything that already satisfies :class:`Executable` is returned as-is.
    """
    if isinstance(target, Executable) and not callable_is_plain_function(target):
        return target

    from phronesis.agents import Agent

    if isinstance(target, Agent):
        return agent_node(target)

    if callable(target):
        return callable_node(target)

    raise TypeError(f"cannot adapt {type(target).__name__!r} to Executable")


def callable_is_plain_function(target: Any) -> bool:
    """Heuristic: bare functions also match ``Executable`` structurally.

    Without this check ``as_node`` would treat ``async def f(x)`` as already
    satisfying the protocol (it is callable and async). We want such
    callables to go through :func:`callable_node` so the (ctx, input)
    signature gets inspected.
    """
    return inspect.isfunction(target) or inspect.ismethod(target)
