"""Shared fixtures for obs tests."""

from __future__ import annotations

from collections.abc import Iterator

import pytest

from phronesis.obs.config import _reset_state
from phronesis.obs.logging_filter import uninstall_trace_correlation_filter


@pytest.fixture(autouse=True)
def _reset_obs_state() -> Iterator[None]:
    _reset_state()
    uninstall_trace_correlation_filter()

    yield

    _reset_state()
    uninstall_trace_correlation_filter()
