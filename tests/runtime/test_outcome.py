"""Tests for RunOutcome: ok/fail, merge_children, metadata."""

from __future__ import annotations

from phronesis.providers.usage import TokenUsage
from phronesis.runtime import RunOutcome


class TestRunOutcome:
    def test_ok_marks_success(self) -> None:
        outcome = RunOutcome.ok(output=42)

        assert outcome.success is True
        assert outcome.error is None
        assert outcome.output == 42

    def test_fail_marks_failure_and_keeps_error(self) -> None:
        err = ValueError("boom")
        outcome = RunOutcome.fail(error=err, output="partial")

        assert outcome.success is False
        assert outcome.error is err
        assert outcome.output == "partial"

    def test_merge_children_sums_tokens(self) -> None:
        c1 = RunOutcome.ok(tokens=TokenUsage(input_tokens=10, output_tokens=5))
        c2 = RunOutcome.ok(tokens=TokenUsage(input_tokens=20, output_tokens=7))
        parent = RunOutcome.ok(output="ok", children=(c1, c2))

        merged = parent.merge_children()

        assert merged.tokens.input_tokens == 30
        assert merged.tokens.output_tokens == 12

    def test_merge_children_sums_cost(self) -> None:
        c1 = RunOutcome.ok(cost_usd=0.10)
        c2 = RunOutcome.ok(cost_usd=0.25)
        parent = RunOutcome.ok(children=(c1, c2))

        merged = parent.merge_children()

        assert merged.cost_usd == 0.35

    def test_merge_children_noop_without_children(self) -> None:
        outcome = RunOutcome.ok(output="x")

        merged = outcome.merge_children()

        assert merged is outcome

    def test_metadata_is_read_only(self) -> None:
        outcome = RunOutcome.ok(metadata={"k": "v"})

        try:
            outcome.metadata["k"] = "w"  # type: ignore[index,unused-ignore]
            failed = False
        except TypeError:
            failed = True

        assert failed
