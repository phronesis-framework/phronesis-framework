"""Tests for ``SessionId``."""

from __future__ import annotations

import pytest

from phronesis._internal.ids.id import Id
from phronesis.communication.session_id import SessionId, session_id_generator


class TestSessionId:
    def test_prefix_is_sid(self) -> None:
        assert SessionId.prefix == "SID"

    def test_is_subclass_of_id(self) -> None:
        assert issubclass(SessionId, Id)

    def test_accepts_valid_canonical(self) -> None:
        sid = SessionId("phronesis.sessions.s_001")

        assert sid.canonical == "phronesis.sessions.s_001"

    def test_short_has_sid_prefix(self) -> None:
        sid = SessionId("phronesis.sessions.s_001")

        assert sid.short.startswith("SID-")
        assert len(sid.short) == len("SID-") + 8

    @pytest.mark.parametrize("canonical", ["", "1.bad", "a..b", "X.y"])
    def test_rejects_invalid_canonical(self, canonical: str) -> None:
        with pytest.raises(ValueError):
            SessionId(canonical)


class TestSessionIdGenerator:
    def test_from_canonical_builds_session_id(self) -> None:
        sid = session_id_generator.from_canonical("phronesis.sessions.s_001")

        assert isinstance(sid, SessionId)
        assert sid.canonical == "phronesis.sessions.s_001"

    def test_from_canonical_rejects_invalid(self) -> None:
        with pytest.raises(ValueError):
            session_id_generator.from_canonical("1.bad")
