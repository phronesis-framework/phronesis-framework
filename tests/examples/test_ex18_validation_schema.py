"""Smoke test for ``examples/ex18_validation_schema``."""

from __future__ import annotations

from collections.abc import Callable
from types import ModuleType

import pytest


@pytest.mark.asyncio
async def test_validator_accepts_json(
    load_example: Callable[[str], ModuleType],
    capsys: pytest.CaptureFixture[str],
) -> None:
    module = load_example("ex18_validation_schema")

    await module.main()

    captured = capsys.readouterr()
    assert '"score": 95' in captured.out
