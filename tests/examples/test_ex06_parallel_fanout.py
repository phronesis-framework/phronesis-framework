"""Smoke test for ``examples/ex06_parallel_fanout``."""

from __future__ import annotations

from collections.abc import Callable
from types import ModuleType

import pytest


@pytest.mark.asyncio
async def test_runs_against_cassette(
    load_example: Callable[[str], ModuleType],
    capsys: pytest.CaptureFixture[str],
) -> None:
    module = load_example("ex06_parallel_fanout")

    await module.main()

    captured = capsys.readouterr()
    assert captured.out.count("- ") == 3
