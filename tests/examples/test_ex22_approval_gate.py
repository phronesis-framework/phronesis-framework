"""Smoke test for ``examples/ex22_approval_gate``."""

from __future__ import annotations

from collections.abc import Callable
from types import ModuleType

import pytest


@pytest.mark.asyncio
async def test_auto_approves_draft(
    load_example: Callable[[str], ModuleType],
    capsys: pytest.CaptureFixture[str],
) -> None:
    module = load_example("ex22_approval_gate")

    await module.main()

    captured = capsys.readouterr()
    assert "approved=True" in captured.out
