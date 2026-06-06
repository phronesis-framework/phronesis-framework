"""Phase 3: trader translates the research thesis into a trading plan."""

from __future__ import annotations

from examples.trading_agents.agents._provider import provider
from examples.trading_agents.prompts import SYSTEM_TRADER
from phronesis.agents import agent


@agent(model=provider, system_prompt=SYSTEM_TRADER)
def trader() -> str:
    """Compose a concrete trading plan."""
