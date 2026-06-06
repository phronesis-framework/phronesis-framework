"""Phase 5: portfolio manager emits the final BUY/SELL/HOLD decision."""

from __future__ import annotations

from examples.trading_agents.agents._provider import provider
from examples.trading_agents.prompts import SYSTEM_PORTFOLIO_MGR
from phronesis.agents import agent


@agent(model=provider, system_prompt=SYSTEM_PORTFOLIO_MGR)
def portfolio_manager() -> str:
    """Emit the final trading decision."""
