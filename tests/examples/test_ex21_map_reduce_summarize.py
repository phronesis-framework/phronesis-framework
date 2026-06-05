"""Smoke test for ``examples/ex21_map_reduce_summarize``."""

from __future__ import annotations

from collections.abc import Callable
from types import ModuleType

import pytest


@pytest.mark.asyncio
async def test_three_summaries_joined(
    load_example: Callable[[str], ModuleType],
    capsys: pytest.CaptureFixture[str],
) -> None:
    module = load_example("ex21_map_reduce_summarize")

    await module.main()

    captured = capsys.readouterr()
    assert captured.out.count("|") == 2
