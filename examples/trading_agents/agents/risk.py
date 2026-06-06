"""Phase 4: aggressive/conservative/neutral risk debate plus manager."""

from __future__ import annotations

from examples.trading_agents.agents._provider import provider
from examples.trading_agents.prompts import (
    SYSTEM_AGGRESSIVE,
    SYSTEM_CONSERVATIVE,
    SYSTEM_NEUTRAL,
    SYSTEM_RISK_MGR,
)
from phronesis.agents import agent


@agent(model=provider, system_prompt=SYSTEM_AGGRESSIVE)
def aggressive() -> str:
    """Push for taking the trade with conviction."""


@agent(model=provider, system_prompt=SYSTEM_CONSERVATIVE)
def conservative() -> str:
    """Push to reduce or skip the trade."""


@agent(model=provider, system_prompt=SYSTEM_NEUTRAL)
def neutral() -> str:
    """Balance both sides into a sizing proposal."""


@agent(model=provider, system_prompt=SYSTEM_RISK_MGR)
def risk_manager() -> str:
    """Synthesise the risk debate into a verdict."""
