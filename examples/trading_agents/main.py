"""TradingAgents pipeline reproducing the Xiao et al. (2024) organigram.

Five phases composed with ``runtime.Sequence`` plus the right adapters:

1. Parallel analyst team (fundamental, sentiment, news, technical).
2. Bull vs Bear debate moderated by the research manager.
3. Trader composes a plan.
4. Aggressive vs Conservative vs Neutral risk debate moderated by the
   risk manager.
5. Portfolio manager emits ``DECISION: BUY | SELL | HOLD``.

Run against the committed cassette::

    CASSETTE_PATH=examples/trading_agents/cassette.jsonl \\
      python -m examples.trading_agents.main

Run live against a local Ollama (and refresh the cassette)::

    RECORD_CASSETTE=examples/trading_agents/cassette.jsonl \\
      python -m examples.trading_agents.main
"""

from __future__ import annotations

import asyncio
from typing import Any

from examples.trading_agents.agents import (
    aggressive,
    bear,
    bull,
    conservative,
    fundamental_analyst,
    neutral,
    news_analyst,
    portfolio_manager,
    research_manager,
    risk_manager,
    sentiment_analyst,
    technical_analyst,
    trader,
)
from examples.trading_agents.data import load_ticker_snapshot
from examples.trading_agents.tools import (
    format_snapshot,
    merge_analyst_reports,
    truncate,
)
from phronesis.runtime import (
    Debate,
    ExecutionContext,
    Parallel,
    Sequence,
    agent_node,
    callable_node,
)


async def prepare_brief(snapshot: dict[str, Any]) -> str:
    """Turn the raw snapshot dict into a text brief for the analysts."""
    return format_snapshot(snapshot)


async def merge_reports(reports: tuple[str, ...]) -> str:
    """Collapse the four analyst outputs into a single research brief."""
    return merge_analyst_reports(reports)


async def trim_thesis(thesis: str) -> str:
    """Cap the research thesis before handing it to the trader."""
    return truncate(str(thesis))


async def trim_plan(plan: str) -> str:
    """Cap the trading plan before opening the risk debate."""
    return truncate(str(plan))


async def package_for_portfolio(risk_verdict: str) -> str:
    """Frame the risk verdict as the final input for the portfolio manager."""
    return f"Trader plan + risk review:\n{truncate(str(risk_verdict))}"


def build_pipeline() -> Sequence:
    """Wire the five phases into a single executable Sequence."""
    analyst_team = Parallel(
        nodes=(
            agent_node(fundamental_analyst),
            agent_node(sentiment_analyst),
            agent_node(news_analyst),
            agent_node(technical_analyst),
        ),
    )

    research_debate = Debate(
        participants=(agent_node(bull), agent_node(bear)),
        rounds=2,
        moderator=agent_node(research_manager),
    )

    risk_debate = Debate(
        participants=(
            agent_node(aggressive),
            agent_node(conservative),
            agent_node(neutral),
        ),
        rounds=2,
        moderator=agent_node(risk_manager),
    )

    return Sequence(
        nodes=(
            callable_node(prepare_brief),
            analyst_team,
            callable_node(merge_reports),
            research_debate,
            callable_node(trim_thesis),
            agent_node(trader),
            callable_node(trim_plan),
            risk_debate,
            callable_node(package_for_portfolio),
            agent_node(portfolio_manager),
        ),
    )


async def main(ticker: str = "AAPL", as_of: str = "2024-01-15") -> None:
    """Load the snapshot, drive the pipeline and print the final decision."""
    snapshot = load_ticker_snapshot(ticker, as_of)
    pipeline = build_pipeline()

    ctx = ExecutionContext.new()
    outcome = await pipeline(ctx, snapshot)

    print(outcome.output)


if __name__ == "__main__":
    asyncio.run(main())
