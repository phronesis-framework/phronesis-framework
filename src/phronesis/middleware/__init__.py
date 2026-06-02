"""Provider middleware infrastructure.

Public API:

- :class:`Middleware` - structural type for middleware callables.
- :data:`NextCall` - type alias for the continuation passed to a
  middleware.
- :func:`apply_middleware` - wrap an :class:`LLMProvider` with an
  ordered chain of middlewares.
- :class:`MiddlewareError` - base error class for middleware failures.

Middlewares only intercept ``complete``; ``stream`` and capability
checks pass through to the underlying provider. The first middleware
in the list is the outermost (called first); the last is closest to
the provider.
"""

from __future__ import annotations

from phronesis.middleware.chain import apply_middleware as apply_middleware
from phronesis.middleware.errors import MiddlewareError as MiddlewareError
from phronesis.middleware.protocol import Middleware as Middleware
from phronesis.middleware.protocol import NextCall as NextCall

__all__ = [
    "Middleware",
    "MiddlewareError",
    "NextCall",
    "apply_middleware",
]
