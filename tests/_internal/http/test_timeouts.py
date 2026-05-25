"""Tests for HttpTimeouts."""

from __future__ import annotations

import httpx

from phronesis._internal.http import HttpTimeouts


class TestHttpTimeouts:
    def test_defaults_are_reasonable(self) -> None:
        t = HttpTimeouts()

        assert t.connect == 10.0
        assert t.read == 60.0
        assert t.write == 10.0
        assert t.pool == 5.0

    def test_to_httpx_returns_timeout(self) -> None:
        t = HttpTimeouts(connect=1.0, read=2.0, write=3.0, pool=4.0)
        ht = t.to_httpx()

        assert isinstance(ht, httpx.Timeout)
        assert ht.connect == 1.0
        assert ht.read == 2.0
        assert ht.write == 3.0
        assert ht.pool == 4.0

    def test_none_phase_disables_timeout(self) -> None:
        t = HttpTimeouts(connect=None, read=None, write=None, pool=None)
        ht = t.to_httpx()

        assert ht.connect is None
        assert ht.read is None
