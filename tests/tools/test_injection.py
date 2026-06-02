"""Tests for ``detect_context_param``."""

from __future__ import annotations

from typing import Annotated

import pytest

from phronesis.context.context import Context
from phronesis.tools.errors import ToolDefinitionError
from phronesis.tools.injection import detect_context_param


def _no_params() -> None: ...


def _no_context(x: int, y: str = "x") -> None: ...


def _ctx_short(ctx: Context) -> None: ...


def _ctx_named_c(c: Context) -> None: ...


def _ctx_named_full(context: Context) -> None: ...


def _ctx_with_args(name: str, ctx: Context) -> None: ...


def _ctx_annotated(ctx: Annotated[Context, "runtime"]) -> None: ...


def _ctx_with_default(ctx: Context | None = None) -> None: ...


def _two_contexts(a: Context, b: Context) -> None: ...


def _looks_like_ctx_but_dict(ctx: dict[str, object]) -> None: ...


def _untyped_ctx(ctx) -> None:  # type: ignore[no-untyped-def]
    return None


class TestDetectsContextParam:
    def test_function_without_params_returns_none(self) -> None:
        assert detect_context_param(_no_params) is None

    def test_function_without_context_returns_none(self) -> None:
        assert detect_context_param(_no_context) is None

    def test_short_name_ctx_is_detected(self) -> None:
        assert detect_context_param(_ctx_short) == "ctx"

    def test_one_letter_name_c_is_detected(self) -> None:
        assert detect_context_param(_ctx_named_c) == "c"

    def test_full_name_context_is_detected(self) -> None:
        assert detect_context_param(_ctx_named_full) == "context"

    def test_context_alongside_other_params_is_detected(self) -> None:
        assert detect_context_param(_ctx_with_args) == "ctx"


class TestAnnotatedAndOptional:
    def test_annotated_context_is_detected(self) -> None:
        assert detect_context_param(_ctx_annotated) == "ctx"

    def test_optional_context_with_default_is_not_detected(self) -> None:
        # Union types are not Context - explicit Optional is treated as opt-out
        # because the parameter is no longer a pure Context annotation.
        assert detect_context_param(_ctx_with_default) is None


class TestDetectionIsByTypeNotName:
    def test_dict_named_ctx_is_not_detected(self) -> None:
        assert detect_context_param(_looks_like_ctx_but_dict) is None

    def test_untyped_param_is_not_detected(self) -> None:
        assert detect_context_param(_untyped_ctx) is None


class TestMultipleContextParams:
    def test_two_context_params_raise_definition_error(self) -> None:
        with pytest.raises(ToolDefinitionError) as exc_info:
            detect_context_param(_two_contexts)

        assert exc_info.value.details["parameters"] == ["a", "b"]
