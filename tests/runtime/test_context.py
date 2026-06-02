"""Tests for ExecutionContext: construction, derivation, deadlines, cancel."""

from __future__ import annotations

import asyncio
import logging
import time

from phronesis.runtime import ExecutionContext


class TestExecutionContext:
    def test_new_assigns_unique_run_ids(self) -> None:
        ctx1 = ExecutionContext.new()
        ctx2 = ExecutionContext.new()

        assert ctx1.run_id != ctx2.run_id

    def test_new_defaults(self) -> None:
        ctx = ExecutionContext.new()

        assert ctx.parent_id is None
        assert ctx.deadline is None
        assert isinstance(ctx.cancellation, asyncio.Event)
        assert ctx.metadata == {}
        assert ctx.logger.name == "phronesis.runtime"

    def test_new_accepts_metadata_and_logger(self) -> None:
        custom_logger = logging.getLogger("phronesis.runtime.test")
        ctx = ExecutionContext.new(metadata={"k": "v"}, logger=custom_logger)

        assert ctx.metadata["k"] == "v"
        assert ctx.logger is custom_logger

    def test_new_with_deadline_sets_monotonic_target(self) -> None:
        before = time.monotonic()
        ctx = ExecutionContext.new(deadline_s=2.0)
        after = time.monotonic()

        assert ctx.deadline is not None
        assert before + 1.5 <= ctx.deadline <= after + 2.5

    def test_child_inherits_deadline_and_cancellation(self) -> None:
        root = ExecutionContext.new(deadline_s=5.0)
        child = root.child()

        assert child.parent_id == root.run_id
        assert child.deadline == root.deadline
        assert child.cancellation is root.cancellation

    def test_child_can_replace_metadata(self) -> None:
        root = ExecutionContext.new(metadata={"role": "root"})
        child = root.child(metadata={"role": "child"})

        assert child.metadata["role"] == "child"
        assert root.metadata["role"] == "root"

    def test_remaining_is_none_without_deadline(self) -> None:
        ctx = ExecutionContext.new()

        assert ctx.remaining() is None

    def test_remaining_decreases_with_time(self) -> None:
        ctx = ExecutionContext.new(deadline_s=1.0)

        first = ctx.remaining()
        assert first is not None and first > 0

    def test_cancel_signals_cancellation(self) -> None:
        ctx = ExecutionContext.new()

        assert not ctx.is_cancelled()

        ctx.cancel()

        assert ctx.is_cancelled()

    def test_metadata_is_read_only(self) -> None:
        ctx = ExecutionContext.new(metadata={"k": "v"})

        try:
            ctx.metadata["k"] = "w"  # type: ignore[index,unused-ignore]
            failed = False
        except TypeError:
            failed = True

        assert failed
