"""Tests for OpenTelemetry runtime detection."""

from __future__ import annotations

from phronesis.obs._detect import OBS_AVAILABLE, _probe_opentelemetry


class TestObsAvailableFlag:
    def test_flag_is_boolean(self) -> None:
        assert isinstance(OBS_AVAILABLE, bool)

    def test_flag_matches_current_probe(self) -> None:
        assert OBS_AVAILABLE is _probe_opentelemetry()


class TestProbeOpenTelemetry:
    def test_probe_returns_boolean(self) -> None:
        assert isinstance(_probe_opentelemetry(), bool)

    def test_probe_is_idempotent(self) -> None:
        first = _probe_opentelemetry()
        second = _probe_opentelemetry()

        assert first == second
