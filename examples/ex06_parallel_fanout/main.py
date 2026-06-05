"""Parallel fanout using ``runtime.Parallel``.

Three agents read the same input concurrently from three angles. The mode
returns a list with one outcome per node, in declaration order.
"""

from __future__ import annotations

import asyncio

from examples._shared import build_provider
from phronesis.agents import agent
from phronesis.runtime import ExecutionContext, Parallel, agent_node

provider = build_provider()


@agent(model=provider, system_prompt="Reply with the economic angle in one sentence.")
def economist() -> str:
    """Economic perspective."""


@agent(model=provider, system_prompt="Reply with the ethical angle in one sentence.")
def ethicist() -> str:
    """Ethical perspective."""


@agent(model=provider, system_prompt="Reply with the technical angle in one sentence.")
def engineer() -> str:
    """Technical perspective."""


async def main() -> None:
    """Run the three angles in parallel and print each one."""
    fanout = Parallel(
        nodes=(agent_node(economist), agent_node(ethicist), agent_node(engineer)),
    )

    ctx = ExecutionContext.new()
    outcome = await fanout(ctx, "Self-driving cars on public roads.")

    for angle in outcome.output:
        print("-", angle)


if __name__ == "__main__":
    asyncio.run(main())
