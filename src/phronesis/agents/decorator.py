"""``@agent`` decorator with optional arguments.

The decorator declares an agent from a function whose body is
**ignored** — the function is used purely as a metadata carrier.
Defaults are derived from the function as follows:

* ``__name__`` → default ``name``
* ``__doc__`` → default ``system_prompt`` (stripped via :func:`inspect.getdoc`)
* return annotation → default ``output_type`` (skipped for ``str``,
  ``None`` or unresolvable annotations)
* dotted ``module.qualname`` → canonical id, normalised by
  :func:`canonical_from_function`

Every default can be overridden by a keyword argument. The resulting
:class:`AgentSpec` is validated eagerly by :func:`validate_spec`, the
:class:`Agent` wrapper is built, and the wrapper is registered into
the registry returned by :func:`current_registry`.

The module also defines two private defaults: :data:`_DEFAULT_VERSION`
(``"0.1.0"``) and :data:`_DEFAULT_MAX_ITERATIONS` (``20``).
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
    """Pick a sensible default for ``output_type`` from ``fn``'s return hint.

    Returns ``None`` for missing annotations, ``str``, ``None``,
    forward references that fail to resolve, or anything that is not
    a plain class.
    """
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
    """Combine explicit overrides with defaults derived from ``fn``.

    Every parameter except ``fn`` and ``model`` may be ``None`` to
    request the function-derived default. ``tools`` is materialised
    into a tuple so the resulting spec is hashable/immutable.
    """
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
    """Declare an agent from a function used purely as metadata.

    The decorated function's name, docstring and return annotation
    seed an :class:`AgentSpec`; every keyword argument overrides the
    corresponding default. The resulting :class:`Agent` is validated
    eagerly with :func:`validate_spec` and registered into the
    registry returned by :func:`current_registry`.

    Args:
        model: :class:`LLMProvider` instance that will back every run.
        name: Override for the LLM-facing agent name. Defaults to
            ``fn.__name__``.
        id: Override for the canonical agent id. Defaults to the
            dotted path derived from the function.
        description: Free-form description. Defaults to ``""``.
        system_prompt: System instructions sent on every turn.
            Defaults to ``inspect.getdoc(fn) or ""``.
        tools: Iterable of :class:`Tool` instances bound to the agent.
            Materialised into a tuple. Defaults to empty.
        output_type: Expected structured output type. Defaults to the
            value returned by :func:`_resolve_output_type`.
        max_iterations: Loop iteration cap. Defaults to
            :data:`_DEFAULT_MAX_ITERATIONS`.
        version: Version string for the spec. Defaults to
            :data:`_DEFAULT_VERSION`.

    Returns:
        A decorator that consumes the target function and yields the
        registered :class:`Agent`.

    Raises:
        AgentConfigurationError: if the derived spec fails eager
            validation (e.g. ``model`` does not implement
            :class:`LLMProvider`, duplicate tool ids, non-positive
            ``max_iterations``).
        DuplicateAgentError: if another distinct agent is already
            registered under the resolved id.
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
