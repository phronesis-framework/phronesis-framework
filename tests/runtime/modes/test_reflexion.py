"""Tests for Reflexion mode."""

from __future__ import annotations

from typing import Any

from phronesis.runtime import (
    ExecutionContext,
    Reflexion,
    ValidationFailedError,
    ValidationResult,
    callable_node,
)


class TestReflexion:
    async def test_first_attempt_accepted(self, root_ctx: ExecutionContext) -> None:
        async def actor(_c: ExecutionContext, _v: Any) -> str:
            return "good"

        r = Reflexion(
            actor=callable_node(actor),
            critic=lambda _o: ValidationResult(valid=True),
            max_iterations=3,
        )
        outcome = await r(root_ctx, None)

        assert outcome.success
        assert outcome.output == "good"

    async def test_retry_with_feedback(self, root_ctx: ExecutionContext) -> None:
        calls = {"n": 0}

        async def actor(_c: ExecutionContext, _v: Any) -> str:
            calls["n"] += 1
            return f"v{calls['n']}"

        def critic(o: Any) -> ValidationResult:
            return ValidationResult(valid=o == "v3", feedback="more")

        r = Reflexion(actor=callable_node(actor), critic=critic, max_iterations=5)
        outcome = await r(root_ctx, None)

        assert outcome.success
        assert outcome.output == "v3"

    async def test_exhausts_attempts(self, root_ctx: ExecutionContext) -> None:
        async def actor(_c: ExecutionContext, _v: Any) -> str:
            return "x"

        r = Reflexion(
            actor=callable_node(actor),
            critic=lambda _o: ValidationResult(valid=False, feedback="nope"),
            max_iterations=2,
        )
        outcome = await r(root_ctx, None)

        assert not outcome.success
        assert isinstance(outcome.error, ValidationFailedError)
