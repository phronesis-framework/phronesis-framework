"""Smoke test for ``examples/ex05_sequence_pipeline``."""

from __future__ import annotations

from collections.abc import Callable
from types import ModuleType

import pytest


@pytest.mark.asyncio
async def test_runs_against_cassette(
    load_example: Callable[[str], ModuleType],
    capsys: pytest.CaptureFixture[str],
) -> None:
    module = load_example("ex05_sequence_pipeline")

    await module.main()

    captured = capsys.readouterr()
    assert "Static typing" in captured.out
