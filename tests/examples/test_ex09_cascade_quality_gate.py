"""Smoke test for ``examples/ex09_cascade_quality_gate``."""

from __future__ import annotations

from collections.abc import Callable
from types import ModuleType

import pytest


@pytest.mark.asyncio
async def test_escalates_to_big_model(
    load_example: Callable[[str], ModuleType],
    capsys: pytest.CaptureFixture[str],
) -> None:
    module = load_example("ex09_cascade_quality_gate")

    await module.main()

    captured = capsys.readouterr()
    assert "scattered" in captured.out
