"""Structural type for provider middlewares.

A :class:`Middleware` is any async callable that receives the
:class:`LLMRequest` plus a continuation ``call_next`` and returns an
:class:`LLMResponse`. Middlewares can transform the request before
calling ``call_next``, transform the response after, short-circuit
the chain by not calling ``call_next`` at all, or do both.

The protocol uses :func:`typing.runtime_checkable` so call sites can
verify a candidate with ``isinstance`` when needed, though structural
typing is the canonical contract.
"""

from __future__ import annotations

from collections.abc import Awaitable, Callable
from typing import Protocol, runtime_checkable

from phronesis.providers.types import LLMRequest, LLMResponse

NextCall = Callable[[LLMRequest], Awaitable[LLMResponse]]
"""Continuation callback passed to every :class:`Middleware`.

Implementations call ``await call_next(request)`` to invoke the next
middleware or the underlying provider.
"""


@runtime_checkable
class Middleware(Protocol):
    """Async callable that intercepts a provider's ``complete`` call."""

    async def __call__(
        self,
        request: LLMRequest,
        call_next: NextCall,
    ) -> LLMResponse:
        """Process ``request`` and produce an :class:`LLMResponse`.

        Implementations may:

        * mutate or rebuild ``request`` before invoking
          ``await call_next(new_request)``;
        * inspect or wrap the returned :class:`LLMResponse`;
        * skip the call to ``call_next`` to short-circuit the chain
          (e.g. a cache hit).

        Args:
            request: The incoming :class:`LLMRequest`.
            call_next: Async continuation that runs the rest of the
                chain (the next middleware, or the underlying
                provider's ``complete`` when this is the innermost
                middleware).

        Returns:
            The :class:`LLMResponse` to propagate back up the chain.
        """
        ...
