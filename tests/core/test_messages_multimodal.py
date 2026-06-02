"""Tests for ``ImageBlock`` and ``DocumentBlock``."""

from __future__ import annotations

from dataclasses import FrozenInstanceError

import pytest

from phronesis.core.messages import (
    ContentBlock,
    DocumentBlock,
    ImageBlock,
)


class TestImageBlock:
    def test_defaults(self) -> None:
        block = ImageBlock(data="https://example.com/x.png")

        assert block.media_type == "image/png"
        assert block.source_type == "url"

    def test_base64_source(self) -> None:
        block = ImageBlock(data="iVBORw==", source_type="base64", media_type="image/jpeg")

        assert block.data == "iVBORw=="
        assert block.media_type == "image/jpeg"
        assert block.source_type == "base64"

    def test_frozen(self) -> None:
        block = ImageBlock(data="x")

        with pytest.raises(FrozenInstanceError):
            block.data = "y"  # type: ignore[misc]

    def test_in_content_block_union(self) -> None:
        block: ContentBlock = ImageBlock(data="x")

        assert isinstance(block, ImageBlock)


class TestDocumentBlock:
    def test_defaults(self) -> None:
        block = DocumentBlock(data="https://example.com/x.pdf")

        assert block.media_type == "application/pdf"
        assert block.source_type == "url"

    def test_base64_source(self) -> None:
        block = DocumentBlock(data="JVBE", source_type="base64")

        assert block.source_type == "base64"

    def test_in_content_block_union(self) -> None:
        block: ContentBlock = DocumentBlock(data="x")

        assert isinstance(block, DocumentBlock)
