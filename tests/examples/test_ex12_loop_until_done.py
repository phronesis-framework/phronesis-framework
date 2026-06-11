"""Smoke test for ``examples/ex12_loop_until_done``."""

from __future__ import annotations

from collections.abc import Callable
from types import ModuleType

import pytest


@pytest.mark.asyncio
async def test_reaches_five(
    load_example: Callable[[str], ModuleType],
    capsys: pytest.CaptureFixture[str],
) -> None:
    module = load_example("ex12_loop_until_done")

    await module.main()

    captured = capsys.readouterr()
    assert "final=5" in captured.out
