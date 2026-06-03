"""Tests for Approval mode."""

from __future__ import annotations

import asyncio
from typing import Any

from phronesis.runtime import (
    Approval,
    ApprovalDeniedError,
    ApprovalTimeoutError,
    ExecutionContext,
    callable_node,
)


class TestApproval:
    async def test_approved(self, root_ctx: ExecutionContext) -> None:
        async def node(_c: ExecutionContext, _v: Any) -> str:
            return "candidate"

        a = Approval(node=callable_node(node), approve=lambda _o: True)
        outcome = await a(root_ctx, None)

        assert outcome.success
        assert outcome.output == "candidate"

    async def test_denied(self, root_ctx: ExecutionContext) -> None:
        async def node(_c: ExecutionContext, _v: Any) -> str:
            return "x"

        a = Approval(node=callable_node(node), approve=lambda _o: False)
        outcome = await a(root_ctx, None)

        assert not outcome.success
        assert isinstance(outcome.error, ApprovalDeniedError)

    async def test_timeout(self, root_ctx: ExecutionContext) -> None:
        async def node(_c: ExecutionContext, _v: Any) -> str:
            return "x"

        async def slow(_o: Any) -> bool:
            await asyncio.sleep(0.5)
            return True

        a = Approval(node=callable_node(node), approve=slow, timeout_s=0.01)
        outcome = await a(root_ctx, None)

        assert not outcome.success
        assert isinstance(outcome.error, ApprovalTimeoutError)
