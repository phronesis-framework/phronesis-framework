"""Approval gate using ``runtime.Approval``.

An agent drafts a short message; a sync callable inspects the draft and
either approves it or rejects it. The example uses an auto-approve
predicate so the test stays deterministic.
"""

from __future__ import annotations

import asyncio

from examples._shared import build_provider
from phronesis.agents import agent
from phronesis.runtime import Approval, ExecutionContext, agent_node

provider = build_provider()


@agent(model=provider, system_prompt="Draft a one-sentence release note.")
def drafter() -> str:
    """Produce a draft release note."""


def auto_approve(candidate: str) -> bool:
    """Approve drafts that mention the project name."""
    return "phronesis" in str(candidate).lower()


async def main() -> None:
    """Run the drafter and gate it behind ``auto_approve``."""
    flow = Approval(node=agent_node(drafter), approve=auto_approve, timeout_s=1.0)

    ctx = ExecutionContext.new()
    outcome = await flow(ctx, "v0.1.0 release")

    print(f"approved={outcome.success} output={outcome.output}")


if __name__ == "__main__":
    asyncio.run(main())
