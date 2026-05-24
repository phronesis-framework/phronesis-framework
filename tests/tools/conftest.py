"""Test fixtures for ``tests/tools/``."""

from __future__ import annotations

from collections.abc import Iterator

import pytest

from phronesis.tools.registry import tool_scope


@pytest.fixture(autouse=True)
def _isolated_tool_registry() -> Iterator[None]:
    """Run each test inside an isolated tool registry scope."""
    with tool_scope():
        yield
