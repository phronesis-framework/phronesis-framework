"""TradingAgents agent roster (13 agents grouped by phase)."""

from __future__ import annotations

from examples.trading_agents.agents.analysts import (
    fundamental_analyst,
    news_analyst,
    sentiment_analyst,
    technical_analyst,
)
from examples.trading_agents.agents.portfolio import portfolio_manager
from examples.trading_agents.agents.researchers import (
    bear,
    bull,
    research_manager,
)
from examples.trading_agents.agents.risk import (
    aggressive,
    conservative,
    neutral,
    risk_manager,
)
from examples.trading_agents.agents.trader import trader

__all__ = [
    "aggressive",
    "bear",
    "bull",
    "conservative",
    "fundamental_analyst",
    "neutral",
    "news_analyst",
    "portfolio_manager",
    "research_manager",
    "risk_manager",
    "sentiment_analyst",
    "technical_analyst",
    "trader",
]
