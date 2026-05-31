"""``@tool`` decorator with optional arguments.

The decorator supports both bare ``@tool`` and parameterised
``@tool(name=..., id=..., effects=(...), lazy=True)`` forms. Defaults
are derived from the function as follows:

* ``__name__`` → default :class:`ToolName`
* dotted ``module.qualname`` → canonical :class:`ToolId` via
  :func:`canonical_from_function`
* ``__doc__`` (stripped via :func:`inspect.getdoc`) → default
  ``description``
* ``version`` defaults to :data:`_DEFAULT_VERSION` (``"0.1.0"``).

The canonical input schema is built eagerly via
:func:`build_canonical_schema` unless ``lazy=True``, in which case
the tool defers schema generation until :meth:`Tool.get_schema` is
first called. Either way, the resulting :class:`Tool` is registered
into the registry returned by :func:`current_registry`.
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
    """Combine explicit overrides with defaults derived from ``fn``.

    Each parameter except ``fn`` may be ``None`` to request the
    function-derived default. ``effects`` is materialised into a
    :class:`frozenset` so the resulting spec is hashable. When
    ``input_schema`` is ``None`` the spec is created with an empty
    schema; the wrapper backfills the canonical schema later.
    """
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

    The decorator accepts two forms:

    * ``@tool`` — used directly on a function, returns the built
      :class:`Tool`.
    * ``@tool(...)`` — used with keyword arguments, returns the
      inner decorator which is then applied to the function.

    Args:
        fn: When used as ``@tool``, the function being decorated.
            Always ``None`` when used as ``@tool(...)``.
        name: Override for the LLM-facing tool name. Defaults to
            ``fn.__name__``.
        id: Override for the canonical tool id. Defaults to the
            dotted path derived from ``fn``.
        description: Override for the tool description. Defaults to
            ``inspect.getdoc(fn) or ""``.
        effects: Iterable of :class:`ToolEffect` values declared by
            the tool. Defaults to the empty set.
        version: Free-form version string. Defaults to
            :data:`_DEFAULT_VERSION`.
        lazy: When ``True``, defer canonical schema generation until
            :meth:`Tool.get_schema` is first called.

    Returns:
        The built :class:`Tool` (bare form) or a decorator producing
        a :class:`Tool` (parameterised form).

    Raises:
        ToolDefinitionError: if the function violates a structural
            rule (e.g. declares more than one :class:`Context`
            parameter).
        DuplicateToolError: if another distinct tool is already
            registered under the resolved id.
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
