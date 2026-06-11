"""Routing using ``runtime.Router``.

A keyword classifier picks one of three specialist agents.
"""

from __future__ import annotations

import asyncio

from examples._shared import build_provider
from phronesis.agents import agent
from phronesis.runtime import ExecutionContext, Router, agent_node

provider = build_provider()


@agent(model=provider, system_prompt="Reply as a friendly support engineer.")
def support() -> str:
    """Customer support voice."""


@agent(model=provider, system_prompt="Reply as a billing specialist with payment focus.")
def billing() -> str:
    """Billing voice."""


@agent(model=provider, system_prompt="Reply as a sales rep promoting upgrades.")
def sales() -> str:
    """Sales voice."""


def classify(text: str) -> str:
    """Pick the route based on keywords in ``text``."""
    lowered = str(text).lower()

    if any(w in lowered for w in ("invoice", "refund", "charge", "billing")):
        return "billing"

    if any(w in lowered for w in ("upgrade", "plan", "pricing")):
        return "sales"

    return "support"


async def main() -> None:
    """Route a billing question and print the specialist's reply."""
    router = Router(
        classifier=classify,
        routes={
            "support": agent_node(support),
            "billing": agent_node(billing),
            "sales": agent_node(sales),
        },
        default=agent_node(support),
    )

    ctx = ExecutionContext.new()
    outcome = await router(ctx, "I see a duplicate charge on my last invoice.")

    print(outcome.output)


if __name__ == "__main__":
    asyncio.run(main())
