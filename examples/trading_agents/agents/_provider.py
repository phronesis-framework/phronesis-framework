"""Single shared provider for the entire trading_agents pipeline.

All 13 agents must share the same provider instance so that cassette
replay sees a single FIFO cursor across the whole run. Without this,
each ``agents/*.py`` module would build its own ``ReplayProvider`` and
each provider would re-read the cassette from line 0, producing wrong
outputs and exhausting the file early.
"""

from __future__ import annotations

from examples._shared import build_provider

provider = build_provider()
