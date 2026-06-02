"""Tests for media propagation in ``translate_history``."""

from __future__ import annotations

from phronesis.core.messages import (
    DocumentBlock,
    ImageBlock,
    TextBlock,
    UserMessage,
)
from phronesis.providers.translation import translate_history


class TestMediaPropagation:
    def test_image_block_becomes_media_ref(self) -> None:
        history = (
            UserMessage(
                content=(
                    TextBlock(text="look"),
                    ImageBlock(data="https://x.png"),
                ),
            ),
        )

        result = translate_history(history)

        assert len(result) == 1
        assert result[0].content == "look"
        assert len(result[0].media) == 1
        assert result[0].media[0].kind == "image"
        assert result[0].media[0].data == "https://x.png"
        assert result[0].media[0].source_type == "url"
        assert result[0].media[0].media_type == "image/png"

    def test_document_block_becomes_media_ref(self) -> None:
        history = (
            UserMessage(
                content=(
                    TextBlock(text="see"),
                    DocumentBlock(data="JVBE", source_type="base64"),
                ),
            ),
        )

        result = translate_history(history)

        assert result[0].media[0].kind == "document"
        assert result[0].media[0].source_type == "base64"
        assert result[0].media[0].media_type == "application/pdf"

    def test_no_media_yields_empty_tuple(self) -> None:
        history = (UserMessage(content=(TextBlock(text="hi"),)),)

        result = translate_history(history)

        assert result[0].media == ()
