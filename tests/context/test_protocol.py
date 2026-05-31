"""Tests for the :class:`ContextBuilder` runtime-checkable protocol."""

from __future__ import annotations

import pytest

from phronesis.context.input import BuildInput
from phronesis.context.protocol import ContextBuilder
from phronesis.core.messages import Message


class _DummyBuilder:
    async def build(self, input: BuildInput) -> list[Message]:
        return []


class _NotABuilder:
    pass


class TestContextBuilderRuntimeCheck:
    def test_structural_implementation_satisfies_protocol(self) -> None:
        assert isinstance(_DummyBuilder(), ContextBuilder)

    def test_non_conforming_object_fails(self) -> None:
        assert not isinstance(_NotABuilder(), ContextBuilder)


class TestContextBuilderInvocation:
    @pytest.mark.asyncio
    async def test_dummy_builder_returns_empty_list(self) -> None:
        builder = _DummyBuilder()
        # Minimal input; the dummy ignores it.
        from tests.context.conftest import FakeProvider

        provider = FakeProvider()
        result = await builder.build(
            BuildInput(
                system_prompt="",
                history=(),
                new_input=None,
                provider=provider,
            )
        )

        assert result == []
