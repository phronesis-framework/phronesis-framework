"""Compose middlewares around an existing :class:`LLMProvider`.

:func:`apply_middleware` wraps a provider with a chain of
:class:`Middleware` callables and returns a new object that still
satisfies the :class:`LLMProvider` protocol. The first middleware in
the list is the outermost (called first); the last is closest to the
underlying provider.

Only ``complete`` is intercepted. ``stream``, ``supports``,
``context_window_size``, ``count_tokens`` and ``count_tokens_exact``
pass through to the inner provider unchanged so cancellation,
capability checks and token accounting keep working without
middleware involvement.
"""

from __future__ import annotations

from collections.abc import AsyncIterator, Awaitable, Callable, Sequence
from typing import TYPE_CHECKING

from phronesis.middleware.protocol import Middleware
from phronesis.providers.chunks import LLMChunk
from phronesis.providers.protocol import LLMProvider, ProviderFeature
from phronesis.providers.types import LLMRequest, LLMResponse

if TYPE_CHECKING:
    from phronesis.core.messages import Message


def apply_middleware(
    provider: LLMProvider,
    middlewares: Sequence[Middleware],
) -> LLMProvider:
    """Return a new :class:`LLMProvider` with ``middlewares`` applied.

    Args:
        provider: The underlying provider whose ``complete`` will be
            wrapped.
        middlewares: Ordered sequence of middlewares. The first entry
            wraps the second, and so on; the last entry calls the
            underlying provider directly.

    Returns:
        A new provider object satisfying :class:`LLMProvider`. The
        original ``provider`` is not mutated.
    """
    return _MiddlewareProvider(provider, tuple(middlewares))


class _MiddlewareProvider:
    """Provider wrapper that runs an onion of middlewares on ``complete``."""

    def __init__(
        self,
        inner: LLMProvider,
        middlewares: tuple[Middleware, ...],
    ) -> None:
        self._inner = inner
        self._middlewares = middlewares

    async def complete(self, request: LLMRequest) -> LLMResponse:
        """Dispatch ``request`` through the middleware chain."""

        async def _terminal(req: LLMRequest) -> LLMResponse:
            return await self._inner.complete(req)

        handler: Callable[[LLMRequest], Awaitable[LLMResponse]] = _terminal

        for middleware in reversed(self._middlewares):
            handler = _bind(middleware, handler)

        return await handler(request)

    def stream(self, request: LLMRequest) -> AsyncIterator[LLMChunk]:
        """Pass through to the inner provider unchanged."""
        return self._inner.stream(request)

    def supports(self, feature: ProviderFeature) -> bool:
        """Mirror the inner provider's capability set."""
        return self._inner.supports(feature)

    def context_window_size(self) -> int:
        """Mirror the inner provider's context window size."""
        return self._inner.context_window_size()

    def count_tokens(self, messages: Sequence[Message]) -> int:
        """Mirror the inner provider's token counter."""
        return self._inner.count_tokens(messages)

    async def count_tokens_exact(self, messages: Sequence[Message]) -> int | None:
        """Mirror the inner provider's exact token counter."""
        return await self._inner.count_tokens_exact(messages)


def _bind(
    middleware: Middleware,
    handler: Callable[[LLMRequest], Awaitable[LLMResponse]],
) -> Callable[[LLMRequest], Awaitable[LLMResponse]]:
    async def _wrapped(request: LLMRequest) -> LLMResponse:
        return await middleware(request, handler)

    return _wrapped
