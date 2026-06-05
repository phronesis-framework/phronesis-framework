"""Resilient call chain using ``runtime.Fallback``.

The primary endpoint raises; the fallback returns a cached response.
"""

from __future__ import annotations

import asyncio

from phronesis.runtime import ExecutionContext, Fallback, callable_node


async def primary_endpoint(_: str) -> str:
    """Pretend the primary service is down."""
    raise ConnectionError("primary down")


async def cache_fallback(query: str) -> str:
    """Serve a degraded but valid response from cache."""
    return f"cached:{query}"


async def main() -> None:
    """Run the chain and print whichever node succeeds."""
    chain = Fallback(
        primary=callable_node(primary_endpoint),
        fallbacks=(callable_node(cache_fallback),),
    )

    ctx = ExecutionContext.new()
    outcome = await chain(ctx, "user:42")

    print(outcome.output)


if __name__ == "__main__":
    asyncio.run(main())
