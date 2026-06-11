"""Smoke test for ``examples/ex10_conditional_branch``."""

from __future__ import annotations

from collections.abc import Callable
from types import ModuleType

import pytest


@pytest.mark.asyncio
async def test_question_routes_to_answerer(
    load_example: Callable[[str], ModuleType],
    capsys: pytest.CaptureFixture[str],
) -> None:
    module = load_example("ex10_conditional_branch")

    await module.main()

    captured = capsys.readouterr()
    assert "Paris" in captured.out
