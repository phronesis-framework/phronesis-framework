"""Pydantic-backed validator for tool arguments.

See ``docs/TOOLS-DECISIONS.md`` (D-12, D-26): build a dynamic Pydantic v2
model from the function signature and use it to validate inputs before
the tool runs. On failure, raise :class:`ToolValidationError` carrying the
expected schema of the **affected parameter only** (not the full schema).
"""

from __future__ import annotations

import inspect
import re
from collections.abc import Callable
from typing import Any, NoReturn, get_type_hints

from pydantic import ValidationError, create_model

from phronesis.tools.errors import ToolValidationError
from phronesis.tools.injection import detect_context_param
from phronesis.tools.single_model import get_single_model

_IDENT_RE = re.compile(r"\W")


def _safe_model_name(fn: Callable[..., Any]) -> str:
    return _IDENT_RE.sub("_", f"{fn.__qualname__}_Args")


def _is_validatable(param: inspect.Parameter) -> bool:
    return param.kind not in (
        inspect.Parameter.VAR_POSITIONAL,
        inspect.Parameter.VAR_KEYWORD,
    )


def _build_single_model_validator(
    param_name: str,
    model: type[Any],
) -> Callable[[dict[str, Any]], dict[str, Any]]:
    def validate(values: dict[str, Any]) -> dict[str, Any]:
        raw = values.get(param_name, {})

        if isinstance(raw, model):
            return {param_name: raw}

        try:
            instance = model.model_validate(raw)
        except ValidationError as exc:
            first = exc.errors()[0]
            loc = first.get("loc") or ()
            field = ".".join(str(p) for p in loc) if loc else ""

            raise ToolValidationError(
                f"Invalid argument {field!r}: {first['msg']}" if field else first["msg"],
                details={
                    "field": field,
                    "got_value": first.get("input"),
                },
            ) from exc

        return {param_name: instance}

    return validate


def _collect_fields(fn: Callable[..., Any]) -> dict[str, Any]:
    signature = inspect.signature(fn)
    hints = get_type_hints(fn, include_extras=True)
    context_param = detect_context_param(fn)
    fields: dict[str, Any] = {}

    for name, param in signature.parameters.items():
        if not _is_validatable(param):
            continue

        if name == context_param:
            continue

        annotation = hints.get(name, Any)
        default = param.default if param.default is not inspect.Parameter.empty else ...
        fields[name] = (annotation, default)

    return fields


def _raise_kwargs_validation_error(
    exc: ValidationError,
    properties: dict[str, Any],
) -> NoReturn:
    first = exc.errors()[0]
    loc = first.get("loc") or ()
    field = ".".join(str(p) for p in loc) if loc else ""
    field_schema = properties.get(str(loc[0]), {}) if loc else {}

    raise ToolValidationError(
        f"Invalid argument {field!r}: {first['msg']}" if field else first["msg"],
        details={
            "field": field,
            "expected_schema": field_schema,
            "got_value": first.get("input"),
        },
    ) from exc


def _build_kwargs_validator(
    model: type[Any],
    properties: dict[str, Any],
) -> Callable[[dict[str, Any]], dict[str, Any]]:
    def validate(values: dict[str, Any]) -> dict[str, Any]:
        try:
            instance = model(**values)
        except ValidationError as exc:
            _raise_kwargs_validation_error(exc, properties)

        dumped: dict[str, Any] = instance.model_dump()

        return dumped

    return validate


def build_validator(
    fn: Callable[..., Any],
) -> Callable[[dict[str, Any]], dict[str, Any]]:
    """Return a callable that validates a kwargs dict against ``fn``'s signature.

    Variadic ``*args`` and ``**kwargs`` are skipped: only named parameters
    are validated. Single-model tools (D-12) delegate validation to the
    declared :class:`BaseModel`.
    """
    single = get_single_model(fn)

    if single is not None:
        param_name, model = single

        return _build_single_model_validator(param_name, model)

    fields = _collect_fields(fn)
    model = create_model(_safe_model_name(fn), **fields)
    schema = model.model_json_schema()
    properties = schema.get("properties", {})

    return _build_kwargs_validator(model, properties)
