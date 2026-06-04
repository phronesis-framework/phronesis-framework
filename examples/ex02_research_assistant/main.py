"""Multi-tool research assistant example.

The agent has three tools available and is expected to chain them:

1. ``search(query)`` returns a list of result dicts.
2. ``fetch_url(url)`` returns the page body for one of the results.
3. ``summarize(text, max_words)`` truncates the body into a short blurb.

This exercises the loop's ability to keep tool results in the context
window and reason about which tool to call next.
"""

from __future__ import annotations

import asyncio

from examples._shared import build_provider
from examples.ex02_research_assistant.tools import fetch_url, search, summarize
from phronesis.agents import agent

SYSTEM_PROMPT = (
    "You are a research assistant. To answer the user, you must: "
    "1) call `search` with a relevant query, "
    "2) call `fetch_url` on the most relevant result, "
    "3) call `summarize` on the fetched content, "
    "and only then return the final summary to the user."
)


@agent(
    model=build_provider(),
    tools=(search, fetch_url, summarize),
    system_prompt=SYSTEM_PROMPT,
    max_iterations=8,
)
def researcher() -> str:
    """Answer research questions by chaining search, fetch and summarize."""


async def main() -> None:
    """Run a single research query."""
    result = await researcher.run("What is the Phronesis framework?")

    print(result.output)


if __name__ == "__main__":
    asyncio.run(main())
