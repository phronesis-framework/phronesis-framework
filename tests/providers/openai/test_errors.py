"""Tests for ``phronesis.providers.openai.errors``."""

from __future__ import annotations

from typing import Any

import httpx
import pytest

from phronesis.providers.errors import (
    AuthenticationError,
    BadRequestError,
    ContextWindowExceededError,
    RateLimitError,
    ServerError,
)
from phronesis.providers.openai.errors import translate_response_error


def _response(
    status: int,
    *,
    body: dict[str, Any] | None = None,
    headers: dict[str, str] | None = None,
) -> httpx.Response:
    return httpx.Response(status, json=body or {}, headers=headers or {})


class TestTranslateResponseErrorAuth:
    @pytest.mark.parametrize("status", [401, 403])
    def test_auth_statuses_map_to_authentication_error(self, status: int) -> None:
        err = translate_response_error(
            _response(status, body={"error": {"message": "bad key"}}),
        )

        assert isinstance(err, AuthenticationError)
        assert "bad key" in str(err)


class TestTranslateResponseErrorRateLimit:
    def test_429_maps_to_rate_limit_error(self) -> None:
        err = translate_response_error(
            _response(429, body={"error": {"message": "slow"}}),
        )

        assert isinstance(err, RateLimitError)
        assert err.retry_after_seconds is None

    def test_429_parses_retry_after_header(self) -> None:
        err = translate_response_error(
            _response(
                429,
                body={"error": {"message": "slow"}},
                headers={"retry-after": "2.5"},
            ),
        )

        assert isinstance(err, RateLimitError)
        assert err.retry_after_seconds == 2.5

    def test_429_ignores_invalid_retry_after(self) -> None:
        err = translate_response_error(
            _response(
                429,
                body={"error": {"message": "slow"}},
                headers={"retry-after": "soon"},
            ),
        )

        assert isinstance(err, RateLimitError)
        assert err.retry_after_seconds is None


class TestTranslateResponseErrorContextLength:
    def test_400_with_context_length_code(self) -> None:
        err = translate_response_error(
            _response(
                400,
                body={
                    "error": {
                        "message": "too long",
                        "code": "context_length_exceeded",
                    },
                },
            ),
        )

        assert isinstance(err, ContextWindowExceededError)

    def test_400_with_context_length_message(self) -> None:
        err = translate_response_error(
            _response(
                400,
                body={
                    "error": {"message": "maximum context length is 8192"},
                },
            ),
        )

        assert isinstance(err, ContextWindowExceededError)

    def test_400_without_context_hint_is_bad_request(self) -> None:
        err = translate_response_error(
            _response(400, body={"error": {"message": "bad arg"}}),
        )

        assert isinstance(err, BadRequestError)


class TestTranslateResponseErrorServer:
    @pytest.mark.parametrize("status", [500, 502, 503, 504])
    def test_5xx_maps_to_server_error(self, status: int) -> None:
        err = translate_response_error(
            _response(status, body={"error": {"message": "boom"}}),
        )

        assert isinstance(err, ServerError)


class TestTranslateResponseErrorFallback:
    def test_invalid_json_uses_reason_phrase(self) -> None:
        response = httpx.Response(418, content=b"not-json")
        err = translate_response_error(response)

        assert isinstance(err, BadRequestError)
