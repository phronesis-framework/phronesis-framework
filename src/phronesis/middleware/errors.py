"""Error hierarchy for the :mod:`phronesis.middleware` package.

:class:`MiddlewareError` is the cross-cutting base every
middleware-related failure inherits from.
"""

from __future__ import annotations

from phronesis.errors import PhronesisError


class MiddlewareError(PhronesisError):
    """Base class for every failure originating in :mod:`phronesis.middleware`."""
