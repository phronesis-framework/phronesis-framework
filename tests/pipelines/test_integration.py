"""Integration tests: pipelines containing nested runtime modes."""

from __future__ import annotations

from typing import Any

from phronesis.pipelines import pipeline
from phronesis.runtime import (
    ExecutionContext,
    Parallel,
    Sequence,
    callable_node,
)


async def _inc(_ctx: ExecutionContext, value: Any) -> Any:
    return value + 1


async def _double(_ctx: ExecutionContext, value: Any) -> Any:
    return value * 2


async def _sum_tuple(_ctx: ExecutionContext, value: Any) -> Any:
    return sum(value)


async def _stringify(_ctx: ExecutionContext, value: Any) -> Any:
    return f"result={value}"


class TestPipelineWithNestedRuntimeModes:
    async def test_pipeline_with_nested_parallel(self) -> None:
        fan_out = Parallel(
            nodes=(callable_node(_inc), callable_node(_double)),
        )

        p = pipeline(
            callable_node(_inc),
            fan_out,
            callable_node(_sum_tuple),
            name="parallel-mid",
        )

        outcome = await p.run(1)

        # 1 -> _inc -> 2; _inc(2)=3, _double(2)=4; sum=(3+4)=7
        assert outcome.success
        assert outcome.output == 7

    async def test_pipeline_with_nested_sequence(self) -> None:
        inner = Sequence(nodes=(callable_node(_inc), callable_node(_double)))

        p = pipeline(callable_node(_inc), inner, callable_node(_stringify), name="seq-nested")

        outcome = await p.run(0)

        # 0 -> _inc -> 1; Sequence: 1 -> _inc -> 2 -> _double -> 4; stringify -> "result=4"
        assert outcome.success
        assert outcome.output == "result=4"

    async def test_pipeline_propagates_children(self) -> None:
        p = pipeline(callable_node(_inc), callable_node(_double), name="children")

        outcome = await p.run(1)

        assert outcome.success
        assert len(outcome.children) == 2
