"""Canonical JSON Schema generation for tool inputs.

See ``docs/TOOLS-DECISIONS.md`` (D-19, D-20, D-21, D-22, D-24, D-25):
schema is generated eagerly from the function signature using Pydantic v2,
then post-processed for LLM consumption (inline ``$ref``, drop ``null``
from optional unions). Per-parameter descriptions come from Google-style
docstring ``Args:`` sections, overridden by ``Annotated[T, "..."]``.
"""

from __future__ import annotations

import inspect
import re
from collections.abc import Callable
from typing import Annotated, Any, get_args, get_origin, get_type_hints

from pydantic import Field, create_model

from phronesis.tools.injection import detect_context_param
from phronesis.tools.single_model import get_single_model

_IDENT_RE = re.compile(r"\W")
_ARGS_HEADER_RE = re.compile(r"^\s*Args?:\s*$", re.MULTILINE)
_ARG_LINE_RE = re.compile(r"^\s*([A-Za-z_]\w*)\s*(?:\([^)]*\))?\s*:\s*(.+?)\s*$")
_SECTION_BREAK_RE = re.compile(r"^\s*(Returns?|Raises?|Yields?|Examples?|Notes?):\s*$")


def _safe_model_name(fn: Callable[..., Any]) -> str:
    return _IDENT_RE.sub("_", f"{fn.__qualname__}_Schema")


def _is_schemable(param: inspect.Parameter) -> bool:
    return param.kind not in (
        inspect.Parameter.VAR_POSITIONAL,
        inspect.Parameter.VAR_KEYWORD,
    )


def _parse_google_args(docstring: str | None) -> dict[str, str]:
    if not docstring:
        return {}

    lines = docstring.splitlines()
    args_start: int | None = None

    for idx, line in enumerate(lines):
        if _ARGS_HEADER_RE.match(line):
            args_start = idx + 1
            break

    if args_start is None:
        return {}

    descriptions: dict[str, str] = {}

    for line in lines[args_start:]:
        if _SECTION_BREAK_RE.match(line):
            break

        match = _ARG_LINE_RE.match(line)

        if match is None:
            continue

        descriptions[match.group(1)] = match.group(2)

    return descriptions


def _extract_annotated_description(annotation: Any) -> str | None:
    if get_origin(annotation) is not Annotated:
        return None

    for meta in get_args(annotation)[1:]:
        if isinstance(meta, str):
            return meta

    return None


def _inline_refs(schema: dict[str, Any]) -> dict[str, Any]:
    defs = schema.pop("$defs", None)

    if not defs:
        return schema

    def resolve(node: Any) -> Any:
        if isinstance(node, dict):
            ref = node.get("$ref")

            if isinstance(ref, str) and ref.startswith("#/$defs/"):
                target = defs.get(ref.split("/")[-1], {})

                return resolve(dict(target))

            return {k: resolve(v) for k, v in node.items()}

        if isinstance(node, list):
            return [resolve(item) for item in node]

        return node

    resolved = resolve(schema)
    assert isinstance(resolved, dict)

    return resolved


def _strip_null_from_optional(schema: dict[str, Any]) -> dict[str, Any]:
    properties = schema.get("properties", {})
    required = set(schema.get("required", []))

    for name, prop in properties.items():
        if name in required:
            continue

        any_of = prop.get("anyOf")

        if not any_of:
            continue

        non_null = [variant for variant in any_of if variant.get("type") != "null"]

        if len(non_null) == len(any_of):
            continue

        if len(non_null) == 1:
            collapsed = dict(non_null[0])
            preserved = {k: v for k, v in prop.items() if k != "anyOf"}
            properties[name] = {**collapsed, **preserved}
        else:
            properties[name] = {**prop, "anyOf": non_null}

    return schema


def build_canonical_schema(fn: Callable[..., Any]) -> dict[str, Any]:
    """Build the canonical JSON schema describing ``fn``'s inputs.

    A parameter typed as :class:`Context` is filtered out: it is injected
    by the runtime, not provided by the LLM, so it must not appear in
    the schema. Single-model tools (D-12) report the declared
    :class:`BaseModel`'s own schema verbatim (post-processed).
    """
    single = get_single_model(fn)

    if single is not None:
        _, model = single
        raw_schema = model.model_json_schema()
        inlined = _inline_refs(raw_schema)

        return _strip_null_from_optional(inlined)

    signature = inspect.signature(fn)
    hints = get_type_hints(fn, include_extras=True)
    docstring_descriptions = _parse_google_args(inspect.getdoc(fn))
    context_param = detect_context_param(fn)
    fields: dict[str, Any] = {}

    for name, param in signature.parameters.items():
        if not _is_schemable(param):
            continue

        if name == context_param:
            continue

        annotation = hints.get(name, Any)
        annotated_description = _extract_annotated_description(annotation)
        description = annotated_description or docstring_descriptions.get(name)
        default = param.default if param.default is not inspect.Parameter.empty else ...
        field_info = Field(default=default, description=description)
        fields[name] = (annotation, field_info)

    model = create_model(_safe_model_name(fn), **fields)
    raw_schema = model.model_json_schema()
    inlined = _inline_refs(raw_schema)
    optimized = _strip_null_from_optional(inlined)

    return optimized
