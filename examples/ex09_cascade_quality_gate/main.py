"""Quality cascade using ``runtime.Cascade``.

Try a small model first; if the answer is too short, escalate to a bigger
one. The first node that passes ``acceptance(output)`` wins.
"""

from __future__ import annotations

import asyncio

from examples._shared import build_provider
from phronesis.agents import agent
from phronesis.runtime import Cascade, ExecutionContext, agent_node

provider = build_provider()


@agent(model=provider, system_prompt="Answer in three words.")
def small_model() -> str:
    """Fast, terse model."""


@agent(model=provider, system_prompt="Answer in two full sentences with detail.")
def big_model() -> str:
    """Slow, verbose model."""


def looks_substantive(output: str) -> bool:
    """Accept when the candidate has at least 40 characters."""
    return len(str(output)) >= 40


async def main() -> None:
    """Run the cascade and print the first accepted output."""
    cascade = Cascade(
        nodes=(agent_node(small_model), agent_node(big_model)),
        acceptance=looks_substantive,
    )

    ctx = ExecutionContext.new()
    outcome = await cascade(ctx, "Why is the sky blue?")

    print(outcome.output)


if __name__ == "__main__":
    asyncio.run(main())
