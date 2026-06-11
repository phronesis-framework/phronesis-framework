"""Data layer for the TradingAgents mini-app.

Loads a ticker snapshot from a JSON cache shipped with the example. If
the cache does not exist, falls back to ``yfinance`` (optional extra
``trading``) and writes the result to the cache for future runs.

Tests rely exclusively on the committed cache so they never touch the
network and do not require ``yfinance`` to be installed.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

CACHE_DIR = Path(__file__).parent / "data_cache"


def _cache_path(ticker: str, as_of: str) -> Path:
    return CACHE_DIR / f"{ticker.upper()}_{as_of}.json"


def load_ticker_snapshot(ticker: str, as_of: str) -> dict[str, Any]:
    """Return a ticker snapshot, preferring the local JSON cache.

    Args:
        ticker: Equity symbol (e.g. ``"AAPL"``).
        as_of: ISO date string (e.g. ``"2024-01-15"``).

    Returns:
        Dict with ``ticker``, ``as_of``, ``price``, ``fundamentals``,
        ``news`` and ``indicators`` keys.

    Raises:
        ImportError: when no cached snapshot exists and ``yfinance`` is
            not installed.
    """
    path = _cache_path(ticker, as_of)

    if path.exists():
        with path.open(encoding="utf-8") as fh:
            data: dict[str, Any] = json.load(fh)

        return data

    try:
        import yfinance  # type: ignore[import-not-found]  # noqa: F401
    except ImportError as exc:
        raise ImportError(
            f"No cached snapshot for {ticker} @ {as_of} and 'yfinance' is not "
            "installed. Install the optional extra: pip install "
            "'phronesis-framework[trading]'."
        ) from exc

    snapshot = _fetch_from_yfinance(ticker, as_of)

    CACHE_DIR.mkdir(parents=True, exist_ok=True)

    with path.open("w", encoding="utf-8") as fh:
        json.dump(snapshot, fh, indent=2)

    return snapshot


def _fetch_from_yfinance(ticker: str, as_of: str) -> dict[str, Any]:
    """Fetch a snapshot live from yfinance.

    Kept in a private helper so tests can stay yfinance-free.
    """
    import yfinance as yf

    handle = yf.Ticker(ticker)
    history = handle.history(start=as_of, period="1d")
    info = handle.info or {}
    news_raw = handle.news or []

    if history.empty:
        price = {"open": 0.0, "close": 0.0, "high": 0.0, "low": 0.0, "volume": 0}
    else:
        row = history.iloc[0]
        price = {
            "open": float(row.get("Open", 0.0)),
            "close": float(row.get("Close", 0.0)),
            "high": float(row.get("High", 0.0)),
            "low": float(row.get("Low", 0.0)),
            "volume": int(row.get("Volume", 0)),
        }

    fundamentals = {
        "pe": info.get("trailingPE"),
        "eps": info.get("trailingEps"),
        "market_cap_b": (info.get("marketCap") or 0) / 1_000_000_000,
        "dividend_yield": info.get("dividendYield"),
        "revenue_growth_yoy": info.get("revenueGrowth"),
        "profit_margin": info.get("profitMargins"),
    }

    news = [
        {
            "title": item.get("title", ""),
            "publisher": item.get("publisher", ""),
            "ts": item.get("providerPublishTime", ""),
        }
        for item in news_raw[:5]
    ]

    return {
        "ticker": ticker.upper(),
        "as_of": as_of,
        "price": price,
        "fundamentals": fundamentals,
        "news": news,
        "indicators": {},
    }
