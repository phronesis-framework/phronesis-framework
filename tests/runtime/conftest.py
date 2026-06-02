"""Shared fixtures for runtime tests."""

from __future__ import annotations

from collections.abc import Callable
from typing import Any

import pytest

from phronesis.runtime import ExecutionContext, RunOutcome, callable_node
from phronesis.runtime.protocol import Executable


async def _echo(_ctx: ExecutionContext, value: Any) -> Any:
    return value


async def _const_factory(constant: Any) -> Any:
    async def _const(_ctx: ExecutionContext, _value: Any) -> Any:
        return constant

    return _const


@pytest.fixture
def echo_node() -> Executable:
    return callable_node(_echo)


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


@pytest.fixture
def make_outcome_node() -> Callable[[RunOutcome], Executable]:
    def _make(outcome: RunOutcome) -> Executable:
        async def _node(_ctx: ExecutionContext, _value: Any) -> RunOutcome:
            return outcome

        return callable_node(_node)

    return _make


@pytest.fixture
def root_ctx() -> ExecutionContext:
    return ExecutionContext.new()
