"""Smoke test for ``examples/ex04_bull_vs_bear_debate``."""

from __future__ import annotations

from collections.abc import Callable
from types import ModuleType

import pytest


@pytest.mark.asyncio
async def test_runs_against_cassette(
    load_example: Callable[[str], ModuleType],
    capsys: pytest.CaptureFixture[str],
) -> None:
    module = load_example("ex04_bull_vs_bear_debate")

    await module.main()

    captured = capsys.readouterr()
    assert "Verdict" in captured.out
