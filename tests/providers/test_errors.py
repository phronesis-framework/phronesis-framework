"""Tests for ``phronesis.providers.errors``."""

from __future__ import annotations

import pytest

from phronesis.providers.errors import (
    AuthenticationError,
    BadRequestError,
    ContextWindowExceededError,
    ProviderError,
    RateLimitError,
    ServerError,
    StreamError,
    TransportError,
)


class TestProviderErrorHierarchy:
    @pytest.mark.parametrize(
        "subclass",
        [
            TransportError,
            AuthenticationError,
            RateLimitError,
            ContextWindowExceededError,
            ServerError,
            BadRequestError,
            StreamError,
        ],
    )
    def test_subclass_inherits_from_provider_error(
        self,
        subclass: type[ProviderError],
    ) -> None:
        assert issubclass(subclass, ProviderError)
        assert issubclass(subclass, Exception)

    def test_provider_error_is_exception(self) -> None:
        assert issubclass(ProviderError, Exception)

    def test_raises_and_catches_by_base(self) -> None:
        with pytest.raises(ProviderError):
            raise TransportError("boom")


class TestRateLimitError:
    def test_default_retry_after_is_none(self) -> None:
        error = RateLimitError("quota exceeded")

        assert error.retry_after_seconds is None
        assert str(error) == "quota exceeded"

    def test_retry_after_seconds_is_stored(self) -> None:
        error = RateLimitError("slow down", retry_after_seconds=2.5)

        assert error.retry_after_seconds == 2.5

    def test_retry_after_is_keyword_only(self) -> None:
        with pytest.raises(TypeError):
            RateLimitError("msg", 1.0)  # type: ignore[misc]
