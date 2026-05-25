"""Detection of :class:`Context`-typed parameters for runtime injection.

See ``docs/TOOLS-DECISIONS.md`` (D-15, D-16, D-17, D-18): a tool that
declares a parameter typed as :class:`Context` receives it from the
runtime via :meth:`Tool.invoke`, and the parameter is filtered out of
the schema and the argument validator.

Detection is by **type**, not by name: any parameter whose resolved
annotation is :class:`Context` (or a subclass) qualifies, regardless of
its identifier (``ctx``, ``context``, ``c``, ...).
"""

from __future__ import annotations

import inspect
from collections.abc import Callable
from typing import Annotated, Any, get_args, get_origin, get_type_hints

from phronesis.context.context import Context
from phronesis.tools.errors import ToolDefinitionError


def _unwrap_annotated(annotation: Any) -> Any:
    if get_origin(annotation) is Annotated:
        return get_args(annotation)[0]

    return annotation


def _is_context_type(annotation: Any) -> bool:
    actual = _unwrap_annotated(annotation)

    if not isinstance(actual, type):
        return False

    return issubclass(actual, Context)


def detect_context_param(fn: Callable[..., Any]) -> str | None:
    """Return the name of the parameter typed as :class:`Context`, if any.

    Returns ``None`` when the function takes no such parameter. Raises
    :class:`ToolDefinitionError` when more than one parameter is typed as
    :class:`Context`: a tool can only receive one runtime context.
    """
    signature = inspect.signature(fn)
    hints = get_type_hints(fn, include_extras=True)
    matches: list[str] = []

    for name, param in signature.parameters.items():
        if param.kind in (
            inspect.Parameter.VAR_POSITIONAL,
            inspect.Parameter.VAR_KEYWORD,
        ):
            continue

        annotation = hints.get(name)

        if annotation is None:
            continue

        if _is_context_type(annotation):
            matches.append(name)

    if len(matches) > 1:
        raise ToolDefinitionError(
            f"Tool {fn.__qualname__!r} declares more than one Context parameter: {matches!r}",
            details={"parameters": matches},
        )

    return matches[0] if matches else None
