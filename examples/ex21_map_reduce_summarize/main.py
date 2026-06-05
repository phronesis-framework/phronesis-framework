"""Map-reduce summarisation using ``runtime.MapReduce``.

The splitter cuts the input into paragraphs; the mapper agent summarises
each one in parallel; the reducer joins the summaries.
"""

from __future__ import annotations

import asyncio
from collections.abc import Sequence
from typing import Any

from examples._shared import build_provider
from phronesis.agents import agent
from phronesis.runtime import ExecutionContext, MapReduce, agent_node

provider = build_provider()


DOCUMENT = """Phronesis is a Python framework for agentic systems.
It exposes agents, tools, providers and a runtime layer of orchestration modes.
Recorded cassettes allow tests to run without network access."""


@agent(model=provider, system_prompt="Summarise the input in five words or less.")
def summariser() -> str:
    """Summarise one paragraph."""


def split_paragraphs(doc: str) -> Sequence[str]:
    """Split ``doc`` on newlines, dropping empties."""
    return [p.strip() for p in str(doc).splitlines() if p.strip()]


def join_summaries(parts: Sequence[Any]) -> str:
    """Concatenate per-paragraph summaries into a single string."""
    return " | ".join(str(p) for p in parts)


async def main() -> None:
    """Run map-reduce and print the joined summary."""
    flow = MapReduce(
        splitter=split_paragraphs,
        mapper=agent_node(summariser),
        reducer=join_summaries,
    )

    ctx = ExecutionContext.new()
    outcome = await flow(ctx, DOCUMENT)

    print(outcome.output)


if __name__ == "__main__":
    asyncio.run(main())
