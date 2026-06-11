"""Linear pipeline using ``runtime.Sequence``.

Three agents chained: ``researcher`` collects raw bullet points, ``writer``
turns them into prose, ``editor`` tightens the prose.

Each node receives the output of the previous one as its ``input``.
"""

from __future__ import annotations

import asyncio

from examples._shared import build_provider
from phronesis.agents import agent
from phronesis.runtime import ExecutionContext, Sequence, agent_node

provider = build_provider()


@agent(model=provider, system_prompt="List three concise bullet points on the topic.")
def researcher() -> str:
    """Emit three bullet points."""


@agent(model=provider, system_prompt="Turn the bullet points into a short paragraph.")
def writer() -> str:
    """Convert bullets to prose."""


@agent(model=provider, system_prompt="Tighten the paragraph. Keep one sentence.")
def editor() -> str:
    """Shorten the prose."""


async def main() -> None:
    """Run the pipeline and print the editor output."""
    pipeline = Sequence(
        nodes=(agent_node(researcher), agent_node(writer), agent_node(editor)),
    )

    ctx = ExecutionContext.new()
    outcome = await pipeline(ctx, "Benefits of static typing in Python.")

    print(outcome.output)


if __name__ == "__main__":
    asyncio.run(main())
