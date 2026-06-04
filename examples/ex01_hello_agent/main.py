"""Minimal agent + tool example.

Demonstrates the smallest end-to-end Phronesis program:

- A function decorated with :func:`phronesis.tools.tool` becomes a
  callable ``Tool`` the model can invoke.
- A function decorated with :func:`phronesis.agents.agent` becomes
  an ``Agent`` that runs the tool-calling loop against the configured
  provider.
- ``await agent.run(prompt)`` returns a ``Result`` whose ``.output``
  field carries the final assistant text.
"""

from __future__ import annotations

import asyncio

from examples._shared import build_provider
from phronesis.agents import agent
from phronesis.tools import tool


@tool
def add(a: int, b: int) -> int:
    """Sum two integers and return the result."""
    return a + b


@agent(
    model=build_provider(),
    tools=(add,),
    system_prompt="You are a precise calculator. Use the add tool when needed.",
)
def calculator() -> str:
    """Answer arithmetic questions using the add tool."""


async def main() -> None:
    """Run a single arithmetic query against the calculator agent."""
    result = await calculator.run("How much is 17 + 25?")

    print(result.output)


if __name__ == "__main__":
    asyncio.run(main())
