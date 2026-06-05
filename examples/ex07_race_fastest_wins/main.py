"""Race-the-fastest using ``runtime.Race``.

Two callables compete: a fast cache hit and a slow upstream fetch. The
mode returns the first one to finish and cancels the rest.
"""

from __future__ import annotations

import asyncio

from phronesis.runtime import ExecutionContext, Race, callable_node


async def cache_hit(_: str) -> str:
    """Return immediately from a local cache."""
    return "cache: hit"


async def slow_upstream(_: str) -> str:
    """Pretend to call a slow upstream service."""
    await asyncio.sleep(0.5)

    return "upstream: fresh"


async def main() -> None:
    """Run both candidates concurrently and print the winner."""
    race = Race(nodes=(callable_node(cache_hit), callable_node(slow_upstream)))

    ctx = ExecutionContext.new()
    outcome = await race(ctx, "key:42")

    print(outcome.output)


if __name__ == "__main__":
    asyncio.run(main())
