"""Iterative refinement using ``runtime.Loop``.

A counter callable adds one per turn. The loop stops when the output
reaches a target value.
"""

from __future__ import annotations

import asyncio

from phronesis.runtime import ExecutionContext, Loop, callable_node


async def increment(value: int) -> int:
    """Add one to the running value."""
    return value + 1


def below_five(value: int) -> bool:
    """Keep looping while the counter is still below five."""
    return value < 5


async def main() -> None:
    """Run the loop and print how many iterations were needed."""
    loop = Loop(body=callable_node(increment), until=below_five, max_iterations=10)

    ctx = ExecutionContext.new()
    outcome = await loop(ctx, 0)

    print(f"final={outcome.output}")


if __name__ == "__main__":
    asyncio.run(main())
