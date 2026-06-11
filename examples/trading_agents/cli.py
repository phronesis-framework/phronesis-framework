"""Minimal argparse CLI for the TradingAgents mini-app.

Default invocation prints only the portfolio manager decision. Pass
``--verbose`` (``-v``) to dump the output of every phase with section
headers, mirroring the original UI without any of its decoration.

Usage::

    python -m examples.trading_agents --ticker AAPL --as-of 2024-01-15
    python -m examples.trading_agents -v
"""

from __future__ import annotations

import argparse
import asyncio
import sys
from typing import Any

from examples.trading_agents.main import run
from phronesis.runtime import RunOutcome

ANALYST_LABELS = ("Fundamental", "Sentiment", "News", "Technical")

# Index of each phase output inside the top-level ``Sequence`` children.
# Keep in sync with ``build_pipeline`` in ``main.py``.
PHASE_BRIEF = 0
PHASE_ANALYSTS = 1
PHASE_RESEARCH = 3
PHASE_TRADER = 5
PHASE_RISK = 7
PHASE_PORTFOLIO = 9

SECTION_BAR = "=" * 72


def _section(title: str, body: Any) -> None:
    print(f"\n{SECTION_BAR}\n{title}\n{SECTION_BAR}\n{body}")


def _print_verbose(outcome: RunOutcome) -> None:
    children = outcome.children

    _section("PHASE 0 - Snapshot brief", children[PHASE_BRIEF].output)

    analyst_outcome = children[PHASE_ANALYSTS]
    _section("PHASE 1 - Analyst team (parallel)", "")

    for label, child in zip(ANALYST_LABELS, analyst_outcome.children, strict=False):
        print(f"\n[{label}]\n{child.output}")

    _section("PHASE 2 - Research debate -> Manager", children[PHASE_RESEARCH].output)
    _section("PHASE 3 - Trader plan", children[PHASE_TRADER].output)
    _section("PHASE 4 - Risk debate -> Manager", children[PHASE_RISK].output)
    _section("PHASE 5 - Portfolio Manager (FINAL)", children[PHASE_PORTFOLIO].output)


def build_parser() -> argparse.ArgumentParser:
    """Build the argparse parser used by ``cli``."""
    parser = argparse.ArgumentParser(
        prog="python -m examples.trading_agents",
        description=(
            "Run the TradingAgents organigram (13 agents, 5 phases) and print "
            "the final BUY/SELL/HOLD decision."
        ),
    )
    parser.add_argument(
        "--ticker",
        default="AAPL",
        help="Equity symbol (default: AAPL).",
    )
    parser.add_argument(
        "--as-of",
        default="2024-01-15",
        help="Snapshot date in ISO format (default: 2024-01-15).",
    )
    parser.add_argument(
        "-v",
        "--verbose",
        action="store_true",
        help="Print the output of every phase, not just the final decision.",
    )

    return parser


def cli(argv: list[str] | None = None) -> int:
    """Entry point. Returns a process exit code."""
    args = build_parser().parse_args(argv)

    outcome = asyncio.run(run(ticker=args.ticker, as_of=args.as_of))

    if not outcome.success:
        print(f"Pipeline failed: {outcome.error}", file=sys.stderr)

        return 1

    if args.verbose:
        _print_verbose(outcome)
    else:
        print(outcome.output)

    return 0


if __name__ == "__main__":
    sys.exit(cli())
