"""Tests for ``phronesis.providers.anthropic.errors``."""

from __future__ import annotations

from typing import Any

import httpx
import pytest

from phronesis.providers.anthropic.errors import translate_response_error
from phronesis.providers.errors import (
    AuthenticationError,
    BadRequestError,
    ContextWindowExceededError,
    ProviderError,
    RateLimitError,
    ServerError,
)


def _response(
    status: int,
    body: dict[str, Any] | None = None,
    headers: dict[str, str] | None = None,
) -> httpx.Response:
    request = httpx.Request("POST", "https://api.anthropic.com/v1/messages")

    return httpx.Response(status, json=body or {}, headers=headers or {}, request=request)


class TestTranslateResponseError:
    @pytest.mark.parametrize("status", [401, 403])
    def test_auth_status_maps_to_authentication_error(self, status: int) -> None:
        error = translate_response_error(
            _response(status, {"error": {"type": "authentication_error", "message": "bad key"}}),
        )

        assert isinstance(error, AuthenticationError)
        assert "bad key" in str(error)

    def test_429_maps_to_rate_limit_error(self) -> None:
        error = translate_response_error(
            _response(429, {"error": {"type": "rate_limit_error", "message": "slow down"}}),
        )

        assert isinstance(error, RateLimitError)
        assert error.retry_after_seconds is None

    def test_429_with_retry_after_header(self) -> None:
        error = translate_response_error(
            _response(
                429,
                {"error": {"type": "rate_limit_error", "message": "slow"}},
                headers={"retry-after": "2.5"},
            ),
        )

        assert isinstance(error, RateLimitError)
        assert error.retry_after_seconds == 2.5

    def test_429_with_invalid_retry_after_header_ignored(self) -> None:
        error = translate_response_error(
            _response(
                429,
                {"error": {"type": "rate_limit_error", "message": "x"}},
                headers={"retry-after": "soon"},
            ),
        )

        assert isinstance(error, RateLimitError)
        assert error.retry_after_seconds is None

    def test_400_context_length_maps_to_context_window_error(self) -> None:
        error = translate_response_error(
            _response(
                400,
                {
                    "error": {
                        "type": "invalid_request_error",
                        "message": "prompt is too long: 250000 tokens",
                    },
                },
            ),
        )

        assert isinstance(error, ContextWindowExceededError)

    def test_400_generic_maps_to_bad_request_error(self) -> None:
        error = translate_response_error(
            _response(
                400,
                {"error": {"type": "invalid_request_error", "message": "missing field"}},
            ),
        )

        assert isinstance(error, BadRequestError)

    @pytest.mark.parametrize("status", [500, 502, 503, 529])
    def test_5xx_maps_to_server_error(self, status: int) -> None:
        error = translate_response_error(
            _response(status, {"error": {"type": "api_error", "message": "boom"}}),
        )

        assert isinstance(error, ServerError)

    def test_overloaded_error_type_maps_to_server_error(self) -> None:
        error = translate_response_error(
            _response(529, {"error": {"type": "overloaded_error", "message": "busy"}}),
        )

        assert isinstance(error, ServerError)

    def test_returns_provider_error_subclass(self) -> None:
        error = translate_response_error(
            _response(404, {"error": {"type": "not_found_error", "message": "no"}}),
        )

        assert isinstance(error, ProviderError)
        assert isinstance(error, BadRequestError)

    def test_non_json_body_uses_reason_phrase(self) -> None:
        request = httpx.Request("POST", "https://api.anthropic.com/v1/messages")
        response = httpx.Response(503, text="<html>busy</html>", request=request)

        error = translate_response_error(response)

        assert isinstance(error, ServerError)
        assert str(error)

    def test_missing_error_field_falls_back(self) -> None:
        error = translate_response_error(_response(500, {}))

        assert isinstance(error, ServerError)
