"""Tests for :class:`phronesis.memory.DeterministicEmbeddingProvider`."""

from __future__ import annotations

import pytest

from phronesis.memory.vector import (
    DeterministicEmbeddingProvider,
    EmbeddingProvider,
)


class TestProtocol:
    def test_implements_protocol(self) -> None:
        assert isinstance(DeterministicEmbeddingProvider(), EmbeddingProvider)


class TestDimensions:
    def test_dimensions_match_constructor(self) -> None:
        provider = DeterministicEmbeddingProvider(dimensions=8)

        assert provider.dimensions == 8

    def test_invalid_dimensions_raises(self) -> None:
        with pytest.raises(ValueError):
            DeterministicEmbeddingProvider(dimensions=0)


class TestEmbedding:
    @pytest.mark.asyncio
    async def test_embed_returns_one_vector_per_text(self) -> None:
        provider = DeterministicEmbeddingProvider(dimensions=4)

        vectors = await provider.embed(("hello", "world"))

        assert len(vectors) == 2
        assert all(len(v) == 4 for v in vectors)

    @pytest.mark.asyncio
    async def test_embed_is_deterministic(self) -> None:
        provider = DeterministicEmbeddingProvider(dimensions=4)

        first = await provider.embed(("same",))
        second = await provider.embed(("same",))

        assert first == second

    @pytest.mark.asyncio
    async def test_different_texts_produce_different_vectors(self) -> None:
        provider = DeterministicEmbeddingProvider(dimensions=4)

        (a,) = await provider.embed(("a",))
        (b,) = await provider.embed(("b",))

        assert a != b

    @pytest.mark.asyncio
    async def test_components_are_in_unit_range(self) -> None:
        provider = DeterministicEmbeddingProvider(dimensions=32)

        (vector,) = await provider.embed(("anything",))

        assert all(-1.0 <= component <= 1.0 for component in vector)
