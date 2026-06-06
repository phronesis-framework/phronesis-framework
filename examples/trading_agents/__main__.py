"""Make ``python -m examples.trading_agents`` invoke the CLI."""

from __future__ import annotations

import sys

from examples.trading_agents.cli import cli

if __name__ == "__main__":
    sys.exit(cli())
