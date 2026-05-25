"""``@tool`` decorator with optional arguments.

Supports both the bare ``@tool`` and ``@tool(...)`` call forms. Infers
``name``, ``id`` and ``description`` from the wrapped function when not
overridden, and generates the canonical input schema eagerly unless
``lazy=True``.
"""

from __future__ import annotations

import inspect
from collections.abc import Callable, Iterable
from typing import Any, overload

from phronesis._internal.ids.derivation import canonical_from_function
from phronesis.tools.effects import ToolEffect
from phronesis.tools.registry import current_registry
from phronesis.tools.schema import build_canonical_schema
from phronesis.tools.spec import ToolSpec
from phronesis.tools.tool import Tool
from phronesis.tools.tool_id import ToolId, ToolName

_DEFAULT_VERSION = "0.1.0"


def _build_spec(
    fn: Callable[..., Any],
    *,
    name: str | None,
    id: str | None,
    description: str | None,
    effects: Iterable[ToolEffect] | None,
    version: str | None,
    input_schema: dict[str, Any] | None,
) -> ToolSpec:
    resolved_id = ToolId(id) if id is not None else ToolId(canonical_from_function(fn))
    resolved_name = ToolName(name) if name is not None else ToolName(fn.__name__)
    resolved_description = description if description is not None else (inspect.getdoc(fn) or "")
    resolved_effects = frozenset(effects) if effects else frozenset()
    resolved_version = version if version is not None else _DEFAULT_VERSION

    return ToolSpec(
        id=resolved_id,
        name=resolved_name,
        description=resolved_description,
        effects=resolved_effects,
        version=resolved_version,
        input_schema=input_schema if input_schema is not None else {},
    )


@overload
def tool(fn: Callable[..., Any], /) -> Tool: ...


@overload
def tool(
    *,
    name: str | None = None,
    id: str | None = None,
    description: str | None = None,
    effects: Iterable[ToolEffect] | None = None,
    version: str | None = None,
    lazy: bool = False,
) -> Callable[[Callable[..., Any]], Tool]: ...


def tool(
    fn: Callable[..., Any] | None = None,
    /,
    *,
    name: str | None = None,
    id: str | None = None,
    description: str | None = None,
    effects: Iterable[ToolEffect] | None = None,
    version: str | None = None,
    lazy: bool = False,
) -> Tool | Callable[[Callable[..., Any]], Tool]:
    """Decorate a function as a Phronesis tool.

    Accepts both ``@tool`` and ``@tool(name=..., id=..., ..., lazy=True)``.
    """

    def wrap(target: Callable[..., Any]) -> Tool:
        canonical_schema = None if lazy else build_canonical_schema(target)
        spec = _build_spec(
            target,
            name=name,
            id=id,
            description=description,
            effects=effects,
            version=version,
            input_schema=canonical_schema,
        )
        built = Tool(target, spec, lazy=lazy)

        if canonical_schema is not None:
            built._canonical_schema = canonical_schema

        current_registry().register(built)

        return built

    if fn is not None:
        return wrap(fn)

    return wrap
