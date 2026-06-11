"""Smoke test for ``examples/ex16_supervisor_dispatch``."""

from __future__ import annotations

from collections.abc import Callable
from types import ModuleType

import pytest


@pytest.mark.asyncio
async def test_supervisor_routes_to_web(
    load_example: Callable[[str], ModuleType],
    capsys: pytest.CaptureFixture[str],
) -> None:
    module = load_example("ex16_supervisor_dispatch")

    await module.main()

    captured = capsys.readouterr()
    assert "Benchmarks" in captured.out
