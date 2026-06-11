"""Smoke test for ``examples/ex08_fallback_chain``."""

from __future__ import annotations

from collections.abc import Callable
from types import ModuleType

import pytest


@pytest.mark.asyncio
async def test_fallback_used(
    load_example: Callable[[str], ModuleType],
    capsys: pytest.CaptureFixture[str],
) -> None:
    module = load_example("ex08_fallback_chain")

    await module.main()

    captured = capsys.readouterr()
    assert "cached:user:42" in captured.out
