"""Tests for ``phronesis.providers.types.ResponseFormat``."""

from __future__ import annotations

from dataclasses import FrozenInstanceError

import pytest

from phronesis.providers.types import LLMRequest, ResponseFormat


class TestResponseFormatDefaults:
    def test_name_defaults_to_response(self) -> None:
        rf = ResponseFormat(schema={"type": "object"})

        assert rf.name == "response"

    def test_strict_defaults_to_true(self) -> None:
        rf = ResponseFormat(schema={"type": "object"})

        assert rf.strict is True

    def test_round_trips_custom_values(self) -> None:
        rf = ResponseFormat(schema={"type": "object"}, name="answer", strict=False)

        assert rf.name == "answer"
        assert rf.strict is False


class TestResponseFormatImmutability:
    def test_uses_slots(self) -> None:
        assert hasattr(ResponseFormat, "__slots__")
        assert not hasattr(ResponseFormat(schema={}), "__dict__")

    def test_frozen(self) -> None:
        rf = ResponseFormat(schema={})

        with pytest.raises(FrozenInstanceError):
            rf.name = "other"  # type: ignore[misc]


class TestLLMRequestWiring:
    def test_response_format_defaults_to_none(self) -> None:
        req = LLMRequest(model="m", messages=())

        assert req.response_format is None

    def test_response_format_round_trips(self) -> None:
        rf = ResponseFormat(schema={"type": "object"})
        req = LLMRequest(model="m", messages=(), response_format=rf)

        assert req.response_format is rf
