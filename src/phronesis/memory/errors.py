"""Error hierarchy for the :mod:`phronesis.memory` package.

Every error in this module inherits from :class:`MemoryError`, which
in turn extends :class:`phronesis.errors.PhronesisError` so callers
can ``except MemoryError`` to catch any memory-related failure.

Each subclass carries a stable ``code`` attribute mirroring the style
used by :class:`phronesis.tools.errors.ToolError`. Memory errors are
**not** serialised back to the model: they are framework-side
failures surfaced to the agent loop or to the user.
"""

from __future__ import annotations

from phronesis.errors import PhronesisError


class MemoryError(PhronesisError):
    """Base class for every failure originating in :mod:`phronesis.memory`."""

    code: str = "memory_error"


class MemoryKeyError(MemoryError):
    """Requested key was not present in the store."""

    code = "memory_key_not_found"


class MemoryScopeError(MemoryError):
    """Constructed :class:`MemoryScope` violates the level/id invariant."""

    code = "memory_invalid_scope"


class MemoryBackendError(MemoryError):
    """Underlying backend raised an unexpected error.

    Wraps I/O failures, serialisation errors and any other backend
    exception that is not part of the store contract. The original
    exception is preserved via ``__cause__``.
    """

    code = "memory_backend_error"


class CheckpointNotFoundError(MemoryError):
    """Requested checkpoint does not exist in the episodic store."""

    code = "memory_checkpoint_not_found"
