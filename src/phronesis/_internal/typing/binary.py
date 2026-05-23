"""Immutable carrier for non-JSON binary payloads."""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True, slots=True)
class BinaryContent:
    """Raw bytes tagged with an IANA media type (e.g. ``image/png``)."""

    data: bytes
    content_type: str
