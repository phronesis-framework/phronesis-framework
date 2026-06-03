"""Shared fixtures and mocks for :mod:`phronesis.memory` tests."""

from __future__ import annotations

from collections.abc import Sequence
from typing import Any

import pytest

from phronesis.memory.scope import MemoryScope


@pytest.fixture
def session_scope() -> MemoryScope:
    """Return a :class:`MemoryScope` bound to a fixed session id."""
    return MemoryScope.session("SID_test")


@pytest.fixture
def run_scope() -> MemoryScope:
    """Return a :class:`MemoryScope` bound to a fixed run id."""
    return MemoryScope.run("RID_test")


class FakeEmbeddingProvider:
    """Embedding provider mapping fixed texts to fixed vectors."""

    def __init__(self, mapping: dict[str, tuple[float, ...]], dimensions: int) -> None:
        self._mapping = mapping
        self._dimensions = dimensions

    async def embed(self, texts: Sequence[str]) -> tuple[tuple[float, ...], ...]:
        return tuple(self._mapping[text] for text in texts)

    @property
    def dimensions(self) -> int:
        return self._dimensions


class FakeProvider:
    """Stub :class:`phronesis.providers.protocol.LLMProvider` for builder tests."""

    name: str = "fake"

    async def complete(self, request: Any) -> Any:  # pragma: no cover - not used
        raise NotImplementedError

    def stream(self, request: Any) -> Any:  # pragma: no cover - not used
        raise NotImplementedError

    def supports(self, feature: Any) -> bool:  # pragma: no cover
        return False

    def context_window_size(self) -> int:  # pragma: no cover
        return 200_000

    def count_tokens(self, messages: Any) -> int:  # pragma: no cover
        return 0

    async def count_tokens_exact(self, messages: Any) -> int | None:  # pragma: no cover
        return None
