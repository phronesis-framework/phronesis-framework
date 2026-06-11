"""Smoke test for ``examples/trading_agents`` mini-app."""

from __future__ import annotations

from collections.abc import Callable
from types import ModuleType

import pytest


@pytest.mark.asyncio
async def test_pipeline_emits_final_decision(
    load_example: Callable[[str], ModuleType],
    capsys: pytest.CaptureFixture[str],
) -> None:
    module = load_example("trading_agents")

    await module.main()

    captured = capsys.readouterr()

    assert any(verdict in captured.out for verdict in ("BUY", "SELL", "HOLD"))
