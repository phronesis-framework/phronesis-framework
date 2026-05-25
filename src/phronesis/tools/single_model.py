"""Detection of tools that take a single :class:`pydantic.BaseModel` input.

See ``docs/TOOLS-DECISIONS.md`` (D-12): tools may accept either a flat
list of typed parameters (the common 90% case) or a single parameter
typed as a ``BaseModel`` subclass acting as the input root (~10%). The
latter delegates schema generation and validation to the model itself.

A :class:`Context`-typed parameter does not count toward the single-input
rule: it is injected by the runtime and excluded from the LLM-facing
contract.
"""

from __future__ import annotations

import inspect
from collections.abc import Callable
from typing import Annotated, Any, get_args, get_origin, get_type_hints

from pydantic import BaseModel

from phronesis.tools.injection import detect_context_param


def _unwrap_annotated(annotation: Any) -> Any:
    if get_origin(annotation) is Annotated:
        return get_args(annotation)[0]

    return annotation


def _is_base_model_type(annotation: Any) -> bool:
    actual = _unwrap_annotated(annotation)

    if not isinstance(actual, type):
        return False

    return issubclass(actual, BaseModel)


def get_single_model(
    fn: Callable[..., Any],
) -> tuple[str, type[BaseModel]] | None:
    """Return ``(param_name, model)`` if ``fn`` is a single-model tool.

    A single-model tool has exactly one non-``Context`` named parameter
    whose annotation resolves to a :class:`BaseModel` subclass. Variadic
    ``*args``/``**kwargs`` are ignored. Returns ``None`` otherwise.
    """
    signature = inspect.signature(fn)
    hints = get_type_hints(fn, include_extras=True)
    context_param = detect_context_param(fn)
    candidates: list[tuple[str, type[BaseModel]]] = []

    for name, param in signature.parameters.items():
        if param.kind in (
            inspect.Parameter.VAR_POSITIONAL,
            inspect.Parameter.VAR_KEYWORD,
        ):
            continue

        if name == context_param:
            continue

        annotation = hints.get(name)

        if annotation is None:
            return None

        if not _is_base_model_type(annotation):
            return None

        actual = _unwrap_annotated(annotation)
        candidates.append((name, actual))

    if len(candidates) != 1:
        return None

    return candidates[0]
