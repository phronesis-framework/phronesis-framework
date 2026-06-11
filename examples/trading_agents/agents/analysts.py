"""Phase 1: four analysts that run in parallel over the same snapshot."""

from __future__ import annotations

from examples.trading_agents.agents._provider import provider
from examples.trading_agents.prompts import (
    SYSTEM_FUNDAMENTAL,
    SYSTEM_NEWS,
    SYSTEM_SENTIMENT,
    SYSTEM_TECHNICAL,
)
from phronesis.agents import agent


@agent(model=provider, system_prompt=SYSTEM_FUNDAMENTAL)
def fundamental_analyst() -> str:
    """Read fundamentals (P/E, EPS, margins, growth)."""


@agent(model=provider, system_prompt=SYSTEM_SENTIMENT)
def sentiment_analyst() -> str:
    """Read social and market sentiment."""


@agent(model=provider, system_prompt=SYSTEM_NEWS)
def news_analyst() -> str:
    """Read recent headlines."""


@agent(model=provider, system_prompt=SYSTEM_TECHNICAL)
def technical_analyst() -> str:
    """Read SMA, RSI, MACD and Bollinger indicators."""
