"""Supervisor-worker loop using ``runtime.Supervisor``.

A dispatcher emits ``[route:web]`` to delegate to the web worker; on the
next turn it omits the marker, ending the loop.
"""

from __future__ import annotations

import asyncio
from typing import Any

from examples._shared import build_provider
from phronesis.agents import agent
from phronesis.runtime import ExecutionContext, Supervisor, agent_node

provider = build_provider()


@agent(
    model=provider,
    system_prompt=(
        "You are a supervisor. If more research is needed, end your reply with "
        "[route:web]. If the task is done, reply without any marker."
    ),
)
def dispatcher() -> str:
    """Decide whether to delegate or finish."""


@agent(model=provider, system_prompt="You are a web researcher. Return three short findings.")
def web_worker() -> str:
    """Search the web."""


def extract_route(output: Any) -> str | None:
    """Extract a route key from a ``[route:NAME]`` marker."""
    text = str(output)
    marker = "[route:"

    if marker not in text:
        return None

    return text.split(marker, 1)[1].split("]", 1)[0].strip()


async def main() -> None:
    """Run the supervisor and print the final answer."""
    supervisor = Supervisor(
        dispatcher=agent_node(dispatcher),
        workers={"web": agent_node(web_worker)},
        max_iterations=4,
        route_extractor=extract_route,
    )

    ctx = ExecutionContext.new()
    outcome = await supervisor(ctx, "What is the latest LLM benchmark consensus?")

    print(outcome.output)


if __name__ == "__main__":
    asyncio.run(main())
