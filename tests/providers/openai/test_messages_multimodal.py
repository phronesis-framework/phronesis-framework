"""Tests for image emission in OpenAI message translation."""

from __future__ import annotations

from phronesis.providers.openai.messages import to_openai_messages
from phronesis.providers.types import MediaRef, Message, Role


class TestOpenAIImageEmission:
    def test_url_image_becomes_image_url_part(self) -> None:
        msg = Message(
            role=Role.USER,
            content="look",
            media=(MediaRef(kind="image", data="https://x.png", media_type="image/png"),),
        )

        result = to_openai_messages([msg])

        assert result[0]["role"] == "user"
        parts = result[0]["content"]
        assert parts[0] == {"type": "text", "text": "look"}
        assert parts[1] == {"type": "image_url", "image_url": {"url": "https://x.png"}}

    def test_base64_image_becomes_data_url(self) -> None:
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

        result = to_openai_messages([msg])

        parts = result[0]["content"]
        image_part = next(p for p in parts if p.get("type") == "image_url")
        assert image_part["image_url"]["url"] == "data:image/png;base64,iVBORw=="

    def test_no_media_keeps_string_content(self) -> None:
        msg = Message(role=Role.USER, content="hi")

        result = to_openai_messages([msg])

        assert result[0] == {"role": "user", "content": "hi"}

    def test_document_media_is_ignored(self) -> None:
        msg = Message(
            role=Role.USER,
            content="read",
            media=(MediaRef(kind="document", data="https://x.pdf", media_type="application/pdf"),),
        )

        result = to_openai_messages([msg])

        # Documents are not supported on chat completions; degrade to plain text.
        assert result[0] == {"role": "user", "content": "read"}
