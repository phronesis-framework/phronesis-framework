"""Smoke test for ``examples/ex19_plan_and_execute``."""

from __future__ import annotations

from collections.abc import Callable
from types import ModuleType

import pytest


@pytest.mark.asyncio
async def test_three_steps_executed(
    load_example: Callable[[str], ModuleType],
    capsys: pytest.CaptureFixture[str],
) -> None:
    module = load_example("ex19_plan_and_execute")

    await module.main()

    captured = capsys.readouterr()
    assert captured.out.count("- ") == 3
