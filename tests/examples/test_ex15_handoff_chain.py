"""Smoke test for ``examples/ex15_handoff_chain``."""

from __future__ import annotations

from collections.abc import Callable
from types import ModuleType

import pytest


@pytest.mark.asyncio
async def test_handoff_to_billing(
    load_example: Callable[[str], ModuleType],
    capsys: pytest.CaptureFixture[str],
) -> None:
    module = load_example("ex15_handoff_chain")

    await module.main()

    captured = capsys.readouterr()
    assert "refund" in captured.out.lower()
