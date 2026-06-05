"""Branching using ``runtime.Conditional``.

A predicate picks a branch based on the input. Questions ending with
``?`` go to the answerer; everything else goes to the summariser.
"""

from __future__ import annotations

import asyncio

from examples._shared import build_provider
from phronesis.agents import agent
from phronesis.runtime import Conditional, ExecutionContext, agent_node

provider = build_provider()


@agent(model=provider, system_prompt="Answer the question in one sentence.")
def answerer() -> str:
    """Answer factual questions."""


@agent(model=provider, system_prompt="Summarise the text in one sentence.")
def summariser() -> str:
    """Summarise statements."""


def is_question(text: str) -> bool:
    """Treat trailing ``?`` as a question marker."""
    return str(text).rstrip().endswith("?")


async def main() -> None:
    """Run with a question to force the ``on_true`` branch."""
    branch = Conditional(
        predicate=is_question,
        on_true=agent_node(answerer),
        on_false=agent_node(summariser),
    )

    ctx = ExecutionContext.new()
    outcome = await branch(ctx, "What is the capital of France?")

    print(outcome.output)


if __name__ == "__main__":
    asyncio.run(main())
