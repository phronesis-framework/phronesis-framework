"""Beam search using ``runtime.TreeSearch``.

The expander grows three children per node by appending tokens. The
evaluator scores a candidate by its length. Beam-width keeps the top
two; the best path wins.
"""

from __future__ import annotations

import asyncio

from phronesis.runtime import ExecutionContext, TreeSearch, callable_node


async def expand(node: str) -> list[str]:
    """Generate three children by appending one of three tokens."""
    base = str(node)

    return [base + "+a", base + "+b", base + "+c"]


async def evaluate(candidate: str) -> float:
    """Score by length; longer paths win."""
    return float(len(str(candidate)))


async def main() -> None:
    """Run beam search and print the winning path."""
    search = TreeSearch(
        expander=callable_node(expand),
        evaluator=callable_node(evaluate),
        max_depth=2,
        beam_width=2,
    )

    ctx = ExecutionContext.new()
    outcome = await search(ctx, "root")

    print(outcome.output)


if __name__ == "__main__":
    asyncio.run(main())
