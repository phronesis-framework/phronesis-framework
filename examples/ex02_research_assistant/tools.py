"""Stubbed research tools.

The tools return canned data so the example is deterministic without
hitting the network. A real implementation would call a search engine
and an HTTP client; the cassette would record real provider behaviour.
"""

from __future__ import annotations

from phronesis.tools import tool


@tool
def search(query: str) -> list[dict[str, str]]:
    """Search the web and return up to five results."""
    return [
        {
            "title": "Phronesis Framework",
            "url": "https://example.com/phronesis",
            "snippet": "Phronesis is a Python framework for building agentic systems.",
        },
    ]


@tool
def fetch_url(url: str) -> str:
    """Return the textual content of ``url``."""
    return (
        "Phronesis is a Python 3.11+ framework that gives developers the "
        "primitives to build production-grade agents: tools, providers, "
        "runtime modes, memory stores and replay-based testing."
    )


@tool
def summarize(text: str, max_words: int = 25) -> str:
    """Truncate ``text`` to at most ``max_words`` words."""
    return " ".join(text.split()[:max_words])
