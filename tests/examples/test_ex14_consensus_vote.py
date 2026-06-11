"""Smoke test for ``examples/ex14_consensus_vote``."""

from __future__ import annotations

from collections.abc import Callable
from types import ModuleType

import pytest


@pytest.mark.asyncio
async def test_majority_positive(
    load_example: Callable[[str], ModuleType],
    capsys: pytest.CaptureFixture[str],
) -> None:
    module = load_example("ex14_consensus_vote")

    await module.main()

    captured = capsys.readouterr()
    assert "positive" in captured.out
