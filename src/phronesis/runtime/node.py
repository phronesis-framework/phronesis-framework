"""Adapters that turn agents or callables into :class:`Executable` nodes.

The runtime only knows about the :class:`Executable` protocol. Anything
else needs an adapter:

* :func:`agent_node` wraps a :class:`phronesis.agents.Agent` and translates
  its :class:`phronesis.agents.Result` into a :class:`RunOutcome`.
* :func:`callable_node` wraps a coroutine function that takes either
  ``(ctx, input)`` or just ``(input)``. The adapter inspects the signature
  once at registration time.
* :func:`as_node` dispatches to one of the two based on the argument type.
"""

from __future__ import annotations

import inspect
from collections.abc import Awaitable, Callable
from typing import TYPE_CHECKING, Any

from phronesis.runtime.outcome import RunOutcome
from phronesis.runtime.protocol import Executable

if TYPE_CHECKING:
    from phronesis.agents import Agent
    from phronesis.runtime.context import ExecutionContext


class _AgentNode:
    """Adapter from :class:`Agent` to :class:`Executable`."""

    __slots__ = ("_agent",)

    def __init__(self, agent: Agent) -> None:
        self._agent = agent

    async def __call__(self, ctx: ExecutionContext, input: Any) -> RunOutcome:
        from phronesis.agents.run import RunRequest

        request = input if isinstance(input, RunRequest) else RunRequest(input=str(input))
        result = await self._agent.run(request)

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
