"""Smoke test for ``examples/ex11_router_classifier``."""

from __future__ import annotations

from collections.abc import Callable
from types import ModuleType

import pytest


@pytest.mark.asyncio
async def test_billing_route(
    load_example: Callable[[str], ModuleType],
    capsys: pytest.CaptureFixture[str],
) -> None:
    module = load_example("ex11_router_classifier")

    await module.main()

    captured = capsys.readouterr()
    assert "refund" in captured.out.lower()
