"""Smoke test for ``examples/ex20_tree_search_beam``."""

from __future__ import annotations

from collections.abc import Callable
from types import ModuleType

import pytest


@pytest.mark.asyncio
async def test_beam_picks_deep_path(
    load_example: Callable[[str], ModuleType],
    capsys: pytest.CaptureFixture[str],
) -> None:
    module = load_example("ex20_tree_search_beam")

    await module.main()

    captured = capsys.readouterr()
    # Two extensions of "+X" added to "root" = length 10
    assert "root+" in captured.out
    assert captured.out.count("+") == 2
