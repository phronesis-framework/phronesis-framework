"""Tests for :class:`phronesis.context.BuildInput`."""

from __future__ import annotations

from dataclasses import FrozenInstanceError

import pytest

from phronesis.context.input import BuildInput
from phronesis.core.messages import TextBlock, UserMessage
from tests.context.conftest import FakeProvider


class TestBuildInputConstruction:
    def test_holds_provided_fields(self) -> None:
        provider = FakeProvider()
        new_input = UserMessage(content=(TextBlock(text="hi"),))

        build_input = BuildInput(
            system_prompt="sys",
            history=(),
            new_input=new_input,
            provider=provider,
        )

        assert build_input.system_prompt == "sys"
        assert build_input.history == ()
        assert build_input.new_input is new_input
        assert build_input.provider is provider

    def test_history_is_tuple(self) -> None:
        provider = FakeProvider()
        msg = UserMessage(content=(TextBlock(text="x"),))

        build_input = BuildInput(
            system_prompt="",
            history=(msg,),
            new_input=None,
            provider=provider,
        )

        assert isinstance(build_input.history, tuple)
        assert build_input.history == (msg,)


class TestBuildInputImmutability:
    def test_is_frozen(self) -> None:
        provider = FakeProvider()
        build_input = BuildInput(
            system_prompt="",
            history=(),
            new_input=None,
            provider=provider,
        )

        with pytest.raises(FrozenInstanceError):
            build_input.system_prompt = "other"  # type: ignore[misc]

    def test_uses_slots(self) -> None:
        provider = FakeProvider()
        instance = BuildInput(
            system_prompt="",
            history=(),
            new_input=None,
            provider=provider,
        )

        assert hasattr(BuildInput, "__slots__")
        assert not hasattr(instance, "__dict__")
