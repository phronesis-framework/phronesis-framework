"""Optional helper formatters used by adapters between phases.

These are plain pure functions (not ``@tool`` callables) — the agents in
this mini-app are single-turn and do not invoke tools dynamically. They
live here so ``main.py`` stays focused on orchestration.
"""

from __future__ import annotations

from typing import Any

MAX_REPORT_CHARS = 1500


def format_snapshot(snapshot: dict[str, Any]) -> str:
    """Render a ticker snapshot as a compact text brief for the analysts."""
    price = snapshot.get("price", {})
    fundamentals = snapshot.get("fundamentals", {})
    indicators = snapshot.get("indicators", {})
    news = snapshot.get("news", [])

    headlines = "\n".join(f"- {item.get('title', '')}" for item in news[:3]) or "- (none)"

    return (
        f"Ticker: {snapshot.get('ticker', '?')} as of {snapshot.get('as_of', '?')}\n"
        f"Price: close={price.get('close')} open={price.get('open')} "
        f"high={price.get('high')} low={price.get('low')} vol={price.get('volume')}\n"
        f"Fundamentals: P/E={fundamentals.get('pe')} EPS={fundamentals.get('eps')} "
        f"margin={fundamentals.get('profit_margin')} "
        f"rev_growth={fundamentals.get('revenue_growth_yoy')}\n"
        f"Indicators: SMA20={indicators.get('sma_20')} SMA50={indicators.get('sma_50')} "
        f"RSI14={indicators.get('rsi_14')} MACD={indicators.get('macd')}\n"
        f"News:\n{headlines}"
    )


def truncate(text: str, limit: int = MAX_REPORT_CHARS) -> str:
    """Cap a report at ``limit`` chars to keep downstream context manageable."""
    if len(text) <= limit:
        return text

    return text[: limit - 3] + "..."


def merge_analyst_reports(reports: tuple[str, ...]) -> str:
    """Concatenate the four analyst outputs into a single research brief."""
    labels = ("FUNDAMENTAL", "SENTIMENT", "NEWS", "TECHNICAL")
    chunks = [
        f"[{label}]\n{truncate(str(report))}"
        for label, report in zip(labels, reports, strict=False)
    ]

    return "\n\n".join(chunks)
