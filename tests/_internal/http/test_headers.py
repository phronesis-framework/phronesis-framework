"""Tests for default headers and sensitive header redaction."""

from __future__ import annotations

from phronesis import __version__
from phronesis._internal.http import build_default_headers, redact_sensitive_headers


class TestBuildDefaultHeaders:
    def test_includes_user_agent_with_version(self) -> None:
        h = build_default_headers()
        assert h["User-Agent"] == f"phronesis-framework/{__version__}"


class TestRedactSensitiveHeaders:
    def test_redacts_authorization(self) -> None:
        out = redact_sensitive_headers({"Authorization": "Bearer xyz"})
        assert out["Authorization"] == "***"

    def test_redacts_x_api_key_case_insensitive(self) -> None:
        out = redact_sensitive_headers({"X-API-Key": "secret"})
        assert out["X-API-Key"] == "***"

    def test_redacts_cookie_headers(self) -> None:
        out = redact_sensitive_headers({"Cookie": "s=1", "Set-Cookie": "s=1"})
        assert out["Cookie"] == "***"
        assert out["Set-Cookie"] == "***"

    def test_keeps_non_sensitive_headers(self) -> None:
        out = redact_sensitive_headers({"Content-Type": "application/json"})
        assert out["Content-Type"] == "application/json"
