"""Stable internal identifier for a communication session."""

from __future__ import annotations

from phronesis._internal.ids.generator import IdGenerator
from phronesis._internal.ids.id import Id


class SessionId(Id):
    """Identifier for a multi-turn communication session."""

    prefix = "SID"


session_id_generator: IdGenerator[SessionId] = IdGenerator(SessionId)
"""Singleton :class:`IdGenerator` for :class:`SessionId`."""
