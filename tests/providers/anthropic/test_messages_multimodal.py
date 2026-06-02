"""Tests for image/document emission in Anthropic message translation."""

from __future__ import annotations

from phronesis.providers.anthropic.messages import to_anthropic_messages
from phronesis.providers.types import MediaRef, Message, Role


class TestAnthropicImageEmission:
    def test_url_image_block(self) -> None:
        msg = Message(
            role=Role.USER,
            content="look",
            media=(MediaRef(kind="image", data="https://x.png", media_type="image/png"),),
        )

        result, _ = to_anthropic_messages([msg])

        assert result[0]["role"] == "user"
        blocks = result[0]["content"]
        assert blocks[0] == {"type": "text", "text": "look"}
        assert blocks[1] == {
            "type": "image",
            "source": {"type": "url", "url": "https://x.png"},
        }

    def test_base64_image_block(self) -> None:
        msg = Message(
            role=Role.USER,
            content="",
            media=(
                MediaRef(
                    kind="image",
                    data="iVBORw==",
                    media_type="image/png",
                    source_type="base64",
                ),
            ),
        )

        result, _ = to_anthropic_messages([msg])

        # Empty content yields only the image block (no empty text)
        blocks = result[0]["content"]
        # Falls back to inserting empty text block to keep "content" non-empty list.
        assert any(b.get("type") == "image" for b in blocks)
        image_block = next(b for b in blocks if b.get("type") == "image")
        assert image_block["source"] == {
            "type": "base64",
            "media_type": "image/png",
            "data": "iVBORw==",
        }


class TestAnthropicDocumentEmission:
    def test_document_block(self) -> None:
        msg = Message(
            role=Role.USER,
            content="read",
            media=(MediaRef(kind="document", data="https://x.pdf", media_type="application/pdf"),),
        )

        result, _ = to_anthropic_messages([msg])

        blocks = result[0]["content"]
        assert any(b.get("type") == "document" for b in blocks)
