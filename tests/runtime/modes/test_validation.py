"""Tests for Validation mode."""

from __future__ import annotations

from typing import Any

from phronesis.runtime import (
    ExecutionContext,
    Validation,
    ValidationFailedError,
    ValidationResult,
    callable_node,
)


class TestValidation:
    async def test_accepts_first_valid(self, root_ctx: ExecutionContext) -> None:
        async def node(_c: ExecutionContext, _v: Any) -> str:
            return "good"

        v = Validation(
            node=callable_node(node),
            validator=lambda o: ValidationResult(valid=True),
            max_attempts=3,
        )
        outcome = await v(root_ctx, None)

        assert outcome.success
        assert outcome.output == "good"

    async def test_retries_with_feedback(self, root_ctx: ExecutionContext) -> None:
        calls = {"n": 0}

        async def node(_c: ExecutionContext, _v: Any) -> str:
            calls["n"] += 1
            return f"v{calls['n']}"

        def validator(o: Any) -> ValidationResult:
            return ValidationResult(valid=o == "v3", feedback="try harder")

        v = Validation(node=callable_node(node), validator=validator, max_attempts=5)
        outcome = await v(root_ctx, None)

        assert outcome.success
        assert outcome.output == "v3"

    async def test_max_attempts_exhausted_fails(self, root_ctx: ExecutionContext) -> None:
        async def node(_c: ExecutionContext, _v: Any) -> str:
            return "bad"

        v = Validation(
            node=callable_node(node),
            validator=lambda _o: ValidationResult(valid=False, feedback="nope"),
            max_attempts=2,
        )
        outcome = await v(root_ctx, None)

        assert not outcome.success
        assert isinstance(outcome.error, ValidationFailedError)
