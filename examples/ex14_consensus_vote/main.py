"""Majority vote using ``runtime.Consensus``.

Three sentiment classifiers vote on the same text. Default aggregator
picks the majority output; ``min_agreement=0.66`` requires two thirds.
"""

from __future__ import annotations

import asyncio

from examples._shared import build_provider
from phronesis.agents import agent
from phronesis.runtime import Consensus, ExecutionContext, agent_node

provider = build_provider()


@agent(
    model=provider,
    system_prompt="Reply with exactly one word: positive, negative or neutral.",
)
def voter_a() -> str:
    """First classifier."""


@agent(
    model=provider,
    system_prompt="Reply with exactly one word: positive, negative or neutral.",
)
def voter_b() -> str:
    """Second classifier."""


@agent(
    model=provider,
    system_prompt="Reply with exactly one word: positive, negative or neutral.",
)
def voter_c() -> str:
    """Third classifier."""


async def main() -> None:
    """Run the three voters and print the consensus."""
    consensus = Consensus(
        voters=(agent_node(voter_a), agent_node(voter_b), agent_node(voter_c)),
        min_agreement=0.66,
    )

    ctx = ExecutionContext.new()
    outcome = await consensus(ctx, "I absolutely loved the new release; it works flawlessly.")

    print(outcome.output)


if __name__ == "__main__":
    asyncio.run(main())
