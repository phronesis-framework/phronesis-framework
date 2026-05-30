"""``@agent`` decorator with optional arguments.

See ``docs/AGENTS-DECISIONS.md`` (D-01, D-02, D-12): the decorator
declares an agent from a function whose body is **ignored** (Model A).
The function provides:

* ``__name__`` → default ``name``
* ``__doc__`` → default ``system_prompt``
* return annotation → default ``output_type``
* ``module.qualname`` → canonical id (via :func:`canonical_from_function`)

Every override is exposed as a keyword argument. The resulting
:class:`Agent` is eagerly validated and registered in the current
:class:`_AgentRegistry`.
"""

from __future__ import annotations

import inspect
from collections.abc import Callable, Iterable
from typing import Any, get_type_hints

from phronesis._internal.ids.derivation import canonical_from_function
from phronesis.agents.agent import Agent
from phronesis.agents.id import AgentId
from phronesis.agents.registry import current_registry
from phronesis.agents.spec import AgentSpec
from phronesis.agents.validation import validate_spec
from phronesis.providers.protocol import LLMProvider
from phronesis.tools.tool import Tool

_DEFAULT_VERSION = "0.1.0"
_DEFAULT_MAX_ITERATIONS = 20


def _resolve_output_type(fn: Callable[..., Any]) -> type | None:
    try:
        hints = get_type_hints(fn)
    except Exception:
        return None

    annotation = hints.get("return", inspect.Signature.empty)

    if annotation is inspect.Signature.empty:
        return None

    if annotation is None or annotation is type(None):
        return None

    if isinstance(annotation, type) and annotation is not str:
        return annotation

    return None


def _build_spec(
    fn: Callable[..., Any],
    *,
    model: LLMProvider,
    name: str | None,
    id: str | None,
    description: str | None,
    system_prompt: str | None,
    tools: Iterable[Tool] | None,
    output_type: type | None,
    max_iterations: int | None,
    version: str | None,
) -> AgentSpec:
    resolved_id = AgentId(id) if id is not None else AgentId(canonical_from_function(fn))
    resolved_name = name if name is not None else fn.__name__
    resolved_description = description if description is not None else ""
    resolved_prompt = system_prompt if system_prompt is not None else (inspect.getdoc(fn) or "")
    resolved_tools = tuple(tools) if tools is not None else ()
    resolved_output = output_type if output_type is not None else _resolve_output_type(fn)
    resolved_max = max_iterations if max_iterations is not None else _DEFAULT_MAX_ITERATIONS
    resolved_version = version if version is not None else _DEFAULT_VERSION

    return AgentSpec(
        id=resolved_id,
        name=resolved_name,
        model=model,
        system_prompt=resolved_prompt,
        tools=resolved_tools,
        description=resolved_description,
        output_type=resolved_output,
        max_iterations=resolved_max,
        version=resolved_version,
    )


def agent(
    *,
    model: LLMProvider,
    name: str | None = None,
    id: str | None = None,
    description: str | None = None,
    system_prompt: str | None = None,
    tools: Iterable[Tool] | None = None,
    output_type: type | None = None,
    max_iterations: int | None = None,
    version: str | None = None,
) -> Callable[[Callable[..., Any]], Agent]:
    """Declare an agent from a function whose body is ignored.

    The decorated function's name, docstring, and return annotation seed
    the :class:`AgentSpec`. The resulting :class:`Agent` is validated
    eagerly and registered in the active registry.
    """

    def wrap(target: Callable[..., Any]) -> Agent:
        spec = _build_spec(
            target,
            model=model,
            name=name,
            id=id,
            description=description,
            system_prompt=system_prompt,
            tools=tools,
            output_type=output_type,
            max_iterations=max_iterations,
            version=version,
        )
        validate_spec(spec)

        built = Agent(spec)
        current_registry().register(built)

        return built

    return wrap
