"""Plan-and-execute using ``runtime.PlanAndExecute``.

The planner breaks the goal into numbered steps. A custom ``step_extractor``
splits the planner's text by newlines. The executor runs on each step.
"""

from __future__ import annotations

import asyncio
from collections.abc import Sequence
from typing import Any

from examples._shared import build_provider
from phronesis.agents import agent
from phronesis.runtime import ExecutionContext, PlanAndExecute, agent_node

provider = build_provider()


@agent(
    model=provider,
    system_prompt="Break the goal into three short numbered steps, one per line.",
)
def planner() -> str:
    """Decompose the goal."""


@agent(model=provider, system_prompt="Execute the step. Reply with one short sentence.")
def executor() -> str:
    """Execute a step."""


def split_steps(output: Any) -> Sequence[str]:
    """Split the planner's text into individual step prompts."""
    return [line.strip() for line in str(output).splitlines() if line.strip()]


async def main() -> None:
    """Run plan-and-execute and print the per-step outputs."""
    flow = PlanAndExecute(
        planner=agent_node(planner),
        executor=agent_node(executor),
        step_extractor=split_steps,
    )

    ctx = ExecutionContext.new()
    outcome = await flow(ctx, "Bake a chocolate cake.")

    for line in outcome.output:
        print("-", line)


if __name__ == "__main__":
    asyncio.run(main())
