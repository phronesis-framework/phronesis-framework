"""Bull vs Bear debate using ``runtime.Debate``.

Two agents (a bull and a bear) take turns over two rounds, then a third
agent (the moderator) reads the full transcript and produces a verdict.

This exercises the runtime layer:

- ``agent_node`` adapts an ``Agent`` so it satisfies the ``Executable``
  protocol expected by runtime modes.
- ``Debate`` orchestrates the rounds, building a ``transcript`` that
  each participant receives in its payload.
- ``ExecutionContext.new()`` creates a root context to drive the call.
- The returned ``RunOutcome.output`` is the moderator's final text.
"""

from __future__ import annotations

import asyncio

from examples._shared import build_provider
from examples.ex04_bull_vs_bear_debate.prompts import (
    SYSTEM_BEAR,
    SYSTEM_BULL,
    SYSTEM_MODERATOR,
)
from phronesis.agents import agent
from phronesis.runtime import Debate, ExecutionContext, agent_node

provider = build_provider()


@agent(model=provider, system_prompt=SYSTEM_BULL)
def bull() -> str:
    """Argue in favour of the topic."""


@agent(model=provider, system_prompt=SYSTEM_BEAR)
def bear() -> str:
    """Argue against the topic."""


@agent(model=provider, system_prompt=SYSTEM_MODERATOR)
def moderator() -> str:
    """Synthesise the transcript into a verdict."""


async def main() -> None:
    """Run a two-round debate and print the moderator verdict."""
    debate = Debate(
        participants=(agent_node(bull), agent_node(bear)),
        rounds=2,
        moderator=agent_node(moderator),
    )

    ctx = ExecutionContext.new()
    outcome = await debate(ctx, "Should companies adopt a four-day workweek?")

    print(outcome.output)


if __name__ == "__main__":
    asyncio.run(main())
