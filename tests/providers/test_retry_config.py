"""Tests for ``phronesis.providers.retry_config``."""

from __future__ import annotations

import pytest

from phronesis._internal.retry import FixedBackoff, RetryExhaustedError
from phronesis.providers.errors import (
    AuthenticationError,
    RateLimitError,
    ServerError,
    TransportError,
)
from phronesis.providers.retry_config import RetryConfig, build_retry_decorator


class TestRetryConfigDefaults:
    def test_default_max_attempts(self) -> None:
        config = RetryConfig()

        assert config.max_attempts == 3

    def test_default_retryable_exceptions(self) -> None:
        config = RetryConfig()

        assert config.on == (TransportError, RateLimitError, ServerError)

    def test_default_honors_retry_after(self) -> None:
        assert RetryConfig().honor_retry_after is True

    def test_default_backoff_and_should_retry_are_none(self) -> None:
        config = RetryConfig()

        assert config.backoff is None
        assert config.should_retry is None


class TestBuildRetryDecorator:
    @pytest.mark.asyncio
    async def test_retries_on_transport_error_until_success(self) -> None:
        attempts = {"n": 0}
        decorator = build_retry_decorator(RetryConfig(backoff=FixedBackoff(0)))

        @decorator
        async def call() -> str:
            attempts["n"] += 1

            if attempts["n"] < 2:
                raise TransportError("transient")

            return "ok"

        result = await call()

        assert result == "ok"
        assert attempts["n"] == 2

    @pytest.mark.asyncio
    async def test_does_not_retry_non_listed_exception(self) -> None:
        attempts = {"n": 0}
        decorator = build_retry_decorator(RetryConfig(backoff=FixedBackoff(0)))

        @decorator
        async def call() -> None:
            attempts["n"] += 1
            raise AuthenticationError("nope")

        with pytest.raises(AuthenticationError):
            await call()

        assert attempts["n"] == 1

    @pytest.mark.asyncio
    async def test_honors_rate_limit_retry_after(self) -> None:
        calls: list[float] = []
        decorator = build_retry_decorator(
            RetryConfig(max_attempts=2, backoff=FixedBackoff(0)),
        )

        @decorator
        async def call() -> None:
            calls.append(0.0)
            raise RateLimitError("slow down", retry_after_seconds=0.01)

        with pytest.raises(RetryExhaustedError):
            await call()

        assert len(calls) == 2

    @pytest.mark.asyncio
    async def test_should_retry_filter_blocks_retry(self) -> None:
        attempts = {"n": 0}
        decorator = build_retry_decorator(
            RetryConfig(
                backoff=FixedBackoff(0),
                should_retry=lambda exc: "retry" in str(exc),
            ),
        )

        @decorator
        async def call() -> None:
            attempts["n"] += 1
            raise ServerError("permanent")

        with pytest.raises(ServerError):
            await call()

        assert attempts["n"] == 1
