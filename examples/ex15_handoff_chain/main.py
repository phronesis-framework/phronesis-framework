"""Agent handoff using ``runtime.HandoffChain``.

A triage agent decides whether the ticket belongs to ``billing`` or
``tech`` and emits a ``[handoff:X]`` marker. The specialist agent has no
marker and terminates the chain.
"""

from __future__ import annotations

import asyncio
from typing import Any

from examples._shared import build_provider
from phronesis.agents import agent
from phronesis.runtime import ExecutionContext, HandoffChain, agent_node

provider = build_provider()


@agent(
    model=provider,
    system_prompt=(
        "You are triage. Decide whether the ticket is 'billing' or 'tech'. "
        "End your reply with the marker [handoff:billing] or [handoff:tech]."
    ),
)
def triage() -> str:
    """Route the ticket."""


@agent(model=provider, system_prompt="You are billing support. Resolve the issue.")
def billing() -> str:
    """Resolve billing tickets."""


@agent(model=provider, system_prompt="You are tech support. Resolve the issue.")
def tech() -> str:
    """Resolve tech tickets."""


def extract_handoff(output: Any) -> str | None:
    """Extract a target from a ``[handoff:NAME]`` marker in the text."""
    text = str(output)
    marker = "[handoff:"

    if marker not in text:
        return None

    return text.split(marker, 1)[1].split("]", 1)[0].strip()


async def main() -> None:
    """Submit a billing ticket and print the resolution."""
    chain = HandoffChain(
        agents={
            "triage": agent_node(triage),
            "billing": agent_node(billing),
            "tech": agent_node(tech),
        },
        initial="triage",
        max_handoffs=3,
        handoff_extractor=extract_handoff,
    )

    ctx = ExecutionContext.new()
    outcome = await chain(ctx, "I was charged twice for last month's subscription.")

    print(outcome.output)


if __name__ == "__main__":
    asyncio.run(main())
