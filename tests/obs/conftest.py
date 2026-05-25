"""Shared fixtures for obs tests."""

from __future__ import annotations

from collections.abc import Iterator

import pytest

from phronesis.obs.config import _reset_state


@pytest.fixture(autouse=True)
def _reset_obs_state() -> Iterator[None]:
    _reset_state()

    yield

    _reset_state()
