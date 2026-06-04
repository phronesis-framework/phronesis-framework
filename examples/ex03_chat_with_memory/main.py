"""Multi-turn chat using ``agent.session()``.

``Session`` keeps the message history in memory across turns. Each call
to ``session.run(message)`` reuses the accumulated transcript, so the
model can refer to information the user introduced in earlier turns.

This example feeds two scripted user turns to show that the agent
recalls the name the user provided in the first turn when asked again
in the second.
"""

from __future__ import annotations

import asyncio

from examples._shared import build_provider
from phronesis.agents import agent

USER_TURNS = (
    "Hi, my name is Eduardo.",
    "Quick check: what's my name?",
)


@agent(
    model=build_provider(),
    system_prompt=(
        "You are a helpful assistant. Refer to past turns when the user "
        "asks about information they have already shared."
    ),
)
def chat() -> str:
    """Answer the user, using the running session history as context."""


async def main() -> None:
    """Drive a two-turn conversation against the same session."""
    session = chat.session()

    for turn in USER_TURNS:
        result = await session.run(turn)

        print(f"> {turn}")
        print(f"< {result.output}\n")


if __name__ == "__main__":
    asyncio.run(main())
