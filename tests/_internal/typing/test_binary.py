"""Tests for BinaryContent."""

from dataclasses import FrozenInstanceError

import pytest

from phronesis._internal.typing import BinaryContent


class TestBinaryContent:
    def test_holds_data_and_content_type(self) -> None:
        c = BinaryContent(data=b"\x00\x01", content_type="image/png")

        assert c.data == b"\x00\x01"
        assert c.content_type == "image/png"

    def test_is_frozen(self) -> None:
        c = BinaryContent(data=b"", content_type="text/plain")

        with pytest.raises(FrozenInstanceError):
            c.content_type = "application/json"  # type: ignore[misc]

    def test_equality_by_fields(self) -> None:
        a = BinaryContent(data=b"x", content_type="text/plain")
        b = BinaryContent(data=b"x", content_type="text/plain")

        assert a == b

    def test_inequality_on_different_data(self) -> None:
        a = BinaryContent(data=b"x", content_type="text/plain")
        b = BinaryContent(data=b"y", content_type="text/plain")

        assert a != b

    def test_inequality_on_different_content_type(self) -> None:
        a = BinaryContent(data=b"x", content_type="text/plain")
        b = BinaryContent(data=b"x", content_type="text/html")

        assert a != b
