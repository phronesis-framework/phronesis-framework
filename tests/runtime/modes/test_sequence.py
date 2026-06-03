"""Tests for Sequence mode."""

from __future__ import annotations

from collections.abc import Callable
from typing import Any

from phronesis.runtime import (
    ExecutionContext,
    RunOutcome,
    Sequence,
    callable_node,
)
from phronesis.runtime.protocol import Executable


async def _inc(_ctx: ExecutionContext, value: Any) -> Any:
    return value + 1


async def _double(_ctx: ExecutionContext, value: Any) -> Any:
    return value * 2


async def _raise(_ctx: ExecutionContext, _value: Any) -> Any:
    raise RuntimeError("boom")


class TestSequence:
    async def test_empty_sequence_returns_input(self, root_ctx: ExecutionContext) -> None:
        seq = Sequence(nodes=())
        outcome = await seq(root_ctx, "x")

        assert outcome.success
        assert outcome.output == "x"

    async def test_chains_outputs(self, root_ctx: ExecutionContext) -> None:
        seq = Sequence(nodes=(callable_node(_inc), callable_node(_double)))
        outcome = await seq(root_ctx, 1)

        assert outcome.success
        assert outcome.output == 4

    async def test_aborts_on_first_failure(self, root_ctx: ExecutionContext) -> None:
        seq = Sequence(nodes=(callable_node(_inc), callable_node(_raise), callable_node(_double)))
        outcome = await seq(root_ctx, 1)

        assert not outcome.success
        assert isinstance(outcome.error, RuntimeError)
        assert len(outcome.children) == 2

    async def test_cancellation_short_circuits(self, root_ctx: ExecutionContext) -> None:
        root_ctx.cancel()
        seq = Sequence(nodes=(callable_node(_inc),))
        outcome = await seq(root_ctx, 1)

        assert not outcome.success

    async def test_passes_through_outcome(
        self,
        root_ctx: ExecutionContext,
        make_outcome_node: Callable[[RunOutcome], Executable],
    ) -> None:
        explicit = RunOutcome.ok(output="x")
        seq = Sequence(nodes=(make_outcome_node(explicit),))
        outcome = await seq(root_ctx, "init")

        assert outcome.output == "x"
