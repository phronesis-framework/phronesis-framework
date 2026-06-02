"""Tests for the :mod:`phronesis.context.errors` hierarchy."""

from __future__ import annotations

from phronesis.context.errors import (
    CompactionError,
    ContextBuilderError,
    ContextError,
)
from phronesis.errors import PhronesisError


class TestContextErrorHierarchy:
    def test_context_error_is_phronesis_error(self) -> None:
        assert issubclass(ContextError, PhronesisError)

    def test_context_builder_error_is_context_error(self) -> None:
        assert issubclass(ContextBuilderError, ContextError)

    def test_compaction_error_is_context_builder_error(self) -> None:
        assert issubclass(CompactionError, ContextBuilderError)

    def test_compaction_error_is_phronesis_error(self) -> None:
        assert issubclass(CompactionError, PhronesisError)


class TestCompactionErrorBehavior:
    def test_carries_details_and_message(self) -> None:
        err = CompactionError("boom", details={"provider": "FakeProvider", "history_size": 3})

        assert err.message == "boom"
        assert err.details == {"provider": "FakeProvider", "history_size": 3}

    def test_can_be_raised_with_cause(self) -> None:
        cause = RuntimeError("upstream")

        try:
            raise CompactionError("boom", details={}) from cause
        except CompactionError as exc:
            assert exc.__cause__ is cause
