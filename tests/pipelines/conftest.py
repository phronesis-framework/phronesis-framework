"""Shared fixtures for :mod:`phronesis.pipelines` tests."""

from __future__ import annotations

from collections.abc import Callable
from typing import Any

import pytest

from phronesis.runtime import ExecutionContext, callable_node
from phronesis.runtime.protocol import Executable


@pytest.fixture
def root_ctx() -> ExecutionContext:
    return ExecutionContext.new()


@pytest.fixture
def make_const_node() -> Callable[[Any], Executable]:
    def _make(constant: Any) -> Executable:
        async def _const(_ctx: ExecutionContext, _value: Any) -> Any:
            return constant

        return callable_node(_const)

    return _make


@pytest.fixture
def make_failing_node() -> Callable[[Exception], Executable]:
    def _make(exc: Exception) -> Executable:
        async def _fail(_ctx: ExecutionContext, _value: Any) -> Any:
            raise exc

        return callable_node(_fail)

    return _make
