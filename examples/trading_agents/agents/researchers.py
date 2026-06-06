"""Phase 2: bull vs bear debate moderated by a research manager."""

from __future__ import annotations

from examples.trading_agents.agents._provider import provider
from examples.trading_agents.prompts import (
    SYSTEM_BEAR,
    SYSTEM_BULL,
    SYSTEM_RESEARCH_MGR,
)
from phronesis.agents import agent


@agent(model=provider, system_prompt=SYSTEM_BULL)
def bull() -> str:
    """Argue the long case."""


@agent(model=provider, system_prompt=SYSTEM_BEAR)
def bear() -> str:
    """Argue the short or avoid case."""


@agent(model=provider, system_prompt=SYSTEM_RESEARCH_MGR)
def research_manager() -> str:
    """Synthesise the debate into a recommendation."""
