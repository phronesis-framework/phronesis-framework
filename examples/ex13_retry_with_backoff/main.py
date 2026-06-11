"""Retry-with-backoff using ``runtime.Retry``.

A flaky callable fails twice and succeeds on the third attempt. The mode
reinvokes it with exponential backoff until success or ``max_attempts``.
"""

from __future__ import annotations

import asyncio

from phronesis.runtime import ExecutionContext, Retry, callable_node

_attempts = 0


async def flaky(payload: str) -> str:
    """Fail the first two calls, succeed on the third."""
    global _attempts
    _attempts += 1

    if _attempts < 3:
        raise ConnectionError(f"transient failure (attempt {_attempts})")

    return f"ok:{payload}"


async def main() -> None:
    """Retry the flaky call and print attempts used."""
    retry = Retry(
        node=callable_node(flaky),
        max_attempts=5,
        backoff_initial_s=0.01,
        backoff_multiplier=2.0,
        on=(ConnectionError,),
    )

    ctx = ExecutionContext.new()
    outcome = await retry(ctx, "payload")

    print(f"output={outcome.output} attempts={_attempts}")


if __name__ == "__main__":
    asyncio.run(main())
