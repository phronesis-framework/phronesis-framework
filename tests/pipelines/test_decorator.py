"""Tests for the ``@pipeline`` decorator form.

Decorated declarations are kept at module top-level on purpose: just
like :func:`phronesis.agents.agent`, the decorator derives a canonical
id from ``module.qualname`` and the validator rejects ``<locals>``
segments produced by functions defined inside other functions.
"""

from __future__ import annotations

from typing import Any

import pytest

from phronesis.pipelines import Pipeline, pipeline
from phronesis.pipelines.ids import _new_pipeline_id
from phronesis.runtime import ExecutionContext, callable_node


async def _inc(_ctx: ExecutionContext, value: Any) -> Any:
    return value + 1


async def _double(_ctx: ExecutionContext, value: Any) -> Any:
    return value * 2


async def _bare_double(value: Any) -> Any:
    return value * 2


# Top-level decorated declarations -----------------------------------


@pipeline(steps=(callable_node(_inc),))
def deco_named() -> None:
    """Pull data and increment it."""


@pipeline(steps=(callable_node(_inc),), name="explicit")
def deco_renamed() -> None: ...


@pipeline(steps=(callable_node(_inc),))
def deco_no_doc() -> None: ...


_EXPLICIT_ID = _new_pipeline_id("custom")


@pipeline(steps=(callable_node(_inc),), pipeline_id=_EXPLICIT_ID)
def deco_with_explicit_id() -> None: ...


@pipeline(steps=(callable_node(_inc), callable_node(_double)))
def deco_compute() -> None:
    """Increment then double."""


@pipeline(steps=(_bare_double,))
def deco_bare_adaptation() -> None: ...


class TestDecoratorMode:
    def test_decorator_returns_pipeline(self) -> None:
        assert isinstance(deco_named, Pipeline)

    def test_name_defaults_to_function_name(self) -> None:
        assert deco_named.name == "deco_named"

    def test_explicit_name_overrides_function_name(self) -> None:
        assert deco_renamed.name == "explicit"

    def test_description_comes_from_docstring(self) -> None:
        assert deco_named.description == "Pull data and increment it."

    def test_missing_docstring_yields_empty_description(self) -> None:
        assert deco_no_doc.description == ""

    def test_pipeline_id_derives_from_module_qualname(self) -> None:
        assert deco_named.pipeline_id.canonical.endswith(".deco_named")
        assert "tests.pipelines.test_decorator" in deco_named.pipeline_id.canonical

    def test_explicit_pipeline_id_overrides_derivation(self) -> None:
        assert deco_with_explicit_id.pipeline_id is _EXPLICIT_ID

    async def test_decorated_pipeline_runs_steps_in_order(self) -> None:
        outcome = await deco_compute.run(1)

        assert outcome.success
        assert outcome.output == 4

    def test_steps_are_adapted_via_as_node(self) -> None:
        assert len(deco_bare_adaptation.steps) == 1


class TestModeDispatch:
    def test_mixing_positional_and_steps_kw_raises(self) -> None:
        with pytest.raises(TypeError):
            pipeline(callable_node(_inc), steps=(callable_node(_double),), name="bad")

    def test_factory_mode_still_requires_name(self) -> None:
        with pytest.raises(TypeError):
            pipeline(callable_node(_inc))  # type: ignore[call-overload]

    def test_decorator_mode_does_not_require_name(self) -> None:
        decorator = pipeline(steps=(callable_node(_inc),))

        assert callable(decorator)
