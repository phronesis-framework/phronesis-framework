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


@tool
def sustract(a: int, b: int) -> int:
    """Sustract two integers and return the result."""
    return a - b


@tool
def times(a: int, b: int) -> int:
    """Times two integers and return the result."""
    return a * b


@tool
def divide(a: int, b: int) -> int:
    """Divide two integers and return the result."""
    return a % b


@agent(
    model=build_provider(),
    tools=(add, sustract, times, divide),
    system_prompt=(
        "You are a precise calculator. You have four tools: add, sustract, "
        "times and divide. Use them to compute the requested expression. "
        "Always call the tools instead of computing in your head, and only "
        "produce the final answer after running every required step."
    ),
    max_iterations=8,
)
def calculator() -> str:
    """Answer arithmetic questions by chaining the calculator tools."""


async def main() -> None:
    """Run a multi-step arithmetic query against the calculator agent."""
    result = await calculator.run("How much is (17 + 25) * 2 - 4?")

    print(result.output)


if __name__ == "__main__":
    asyncio.run(main())
