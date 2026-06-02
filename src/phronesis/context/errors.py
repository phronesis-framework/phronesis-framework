"""Error hierarchy for the :mod:`phronesis.context` package.

:class:`ContextError` is the cross-cutting base every context-related
failure inherits from. :class:`ContextBuilderError` narrows that to
failures that originate inside a :class:`ContextBuilder` implementation,
and :class:`CompactionError` further narrows it to failures of the
compactor LLM call performed by
:class:`phronesis.context.CompactingContextBuilder`.
"""

from __future__ import annotations

from phronesis.errors import PhronesisError


class ContextError(PhronesisError):
    """Base class for every failure originating in :mod:`phronesis.context`."""


class ContextBuilderError(ContextError):
    """Raised when a :class:`ContextBuilder` cannot produce a message list."""


class CompactionError(ContextBuilderError):
    """Raised when the compactor LLM call fails.

    The originating exception is preserved via ``__cause__``; the
    ``details`` mapping carries the provider name and the size of the
    history that triggered compaction.
    """
