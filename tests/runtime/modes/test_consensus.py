"""Tests for Consensus mode."""

from __future__ import annotations

from typing import Any

from phronesis.runtime import Consensus, ConsensusError, ExecutionContext, callable_node


class TestConsensus:
    async def test_majority_wins(self, root_ctx: ExecutionContext) -> None:
        async def v_yes(_c: ExecutionContext, _v: Any) -> str:
            return "yes"

        async def v_no(_c: ExecutionContext, _v: Any) -> str:
            return "no"

        c = Consensus(
            voters=(
                callable_node(v_yes),
                callable_node(v_yes),
                callable_node(v_no),
            ),
            min_agreement=0.6,
        )
        outcome = await c(root_ctx, None)

        assert outcome.success
        assert outcome.output == "yes"

    async def test_no_consensus_fails(self, root_ctx: ExecutionContext) -> None:
        async def v_yes(_c: ExecutionContext, _v: Any) -> str:
            return "yes"

        async def v_no(_c: ExecutionContext, _v: Any) -> str:
            return "no"

        c = Consensus(
            voters=(callable_node(v_yes), callable_node(v_no)),
            min_agreement=0.9,
        )
        outcome = await c(root_ctx, None)

        assert not outcome.success
        assert isinstance(outcome.error, ConsensusError)

    async def test_custom_aggregator(self, root_ctx: ExecutionContext) -> None:
        async def voter(_c: ExecutionContext, _v: Any) -> int:
            return 5

        c = Consensus(
            voters=(callable_node(voter), callable_node(voter)),
            aggregator=lambda outs: sum(outs),
            min_agreement=0.0,
        )
        outcome = await c(root_ctx, None)

        assert outcome.output == 10
