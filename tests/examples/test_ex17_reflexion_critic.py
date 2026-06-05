"""Smoke test for ``examples/ex17_reflexion_critic``."""

from __future__ import annotations

from collections.abc import Callable
from types import ModuleType

import pytest


@pytest.mark.asyncio
async def test_actor_corrects_until_critic_accepts(
    load_example: Callable[[str], ModuleType],
    capsys: pytest.CaptureFixture[str],
) -> None:
    module = load_example("ex17_reflexion_critic")

    await module.main()

    captured = capsys.readouterr()
    assert "because" in captured.out.lower()
