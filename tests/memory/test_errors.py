"""Tests for the :mod:`phronesis.memory.errors` hierarchy."""

from __future__ import annotations

from phronesis.errors import PhronesisError
from phronesis.memory.errors import (
    CheckpointNotFoundError,
    MemoryBackendError,
    MemoryError,
    MemoryKeyError,
    MemoryScopeError,
)


class TestHierarchy:
    def test_memory_error_is_phronesis_error(self) -> None:
        assert issubclass(MemoryError, PhronesisError)

    def test_subclasses_inherit_memory_error(self) -> None:
        for subclass in (
            MemoryKeyError,
            MemoryScopeError,
            MemoryBackendError,
            CheckpointNotFoundError,
        ):
            assert issubclass(subclass, MemoryError)


class TestCodes:
    def test_codes_are_stable(self) -> None:
        assert MemoryError.code == "memory_error"
        assert MemoryKeyError.code == "memory_key_not_found"
        assert MemoryScopeError.code == "memory_invalid_scope"
        assert MemoryBackendError.code == "memory_backend_error"
        assert CheckpointNotFoundError.code == "memory_checkpoint_not_found"

    def test_details_are_carried(self) -> None:
        err = MemoryKeyError("missing", details={"key": "x"})

        assert err.details == {"key": "x"}
        assert err.message == "missing"
