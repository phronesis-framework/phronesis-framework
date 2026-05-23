"""Binary content carrier for non-JSON tool outputs.

Use :class:`BinaryContent` when a tool's output (image, audio, archive)
cannot be represented as a :data:`JsonValue`. The ``content_type`` is the
IANA media type string (e.g. ``"image/png"``, ``"audio/wav"``,
``"application/pdf"``).

The carrier is immutable so it can be safely shared across the trace,
cache, and transport layers without defensive copying.
"""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True, slots=True)
class BinaryContent:
    """Raw bytes paired with a MIME content type.

    Attributes:
        data: The raw byte payload.
        content_type: IANA media type string describing ``data``.
    """

    data: bytes
    content_type: str
