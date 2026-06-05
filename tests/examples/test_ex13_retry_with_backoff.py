"""Smoke test for ``examples/ex13_retry_with_backoff``."""

from __future__ import annotations

from collections.abc import Callable
from types import ModuleType

import pytest


@pytest.mark.asyncio
async def test_succeeds_on_third_attempt(
    load_example: Callable[[str], ModuleType],
    capsys: pytest.CaptureFixture[str],
) -> None:
    module = load_example("ex13_retry_with_backoff")

    await module.main()

    captured = capsys.readouterr()
    assert "output=ok:payload" in captured.out
    assert "attempts=3" in captured.out
