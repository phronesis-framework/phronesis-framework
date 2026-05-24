"""Invocable wrapper that pairs a callable with its :class:`ToolSpec`.

See ``docs/TOOLS-DECISIONS.md`` (D-01, D-02, D-06): the tool object is the
callable side; ``tool.spec`` is the pure-data side. Sync and async callables
are both supported transparently via ``__call__``.
"""

from __future__ import annotations

import functools
import inspect
from collections.abc import Callable
from typing import Any

from phronesis.context.context import Context
from phronesis.tools.errors import ToolError, ToolValidationError, auto_map_exception
from phronesis.tools.injection import detect_context_param
from phronesis.tools.schema import build_canonical_schema
from phronesis.tools.single_model import get_single_model
from phronesis.tools.spec import ToolSpec
from phronesis.tools.validation import build_validator


class Tool:
    """Callable wrapper exposing a :class:`ToolSpec` as ``self.spec``.

    ``__call__`` delegates to the wrapped function: for sync functions it
    returns the value; for async functions it returns the coroutine, so the
    caller can ``await`` it normally.
    """

    __wrapped__: Callable[..., Any]
    __name__: str

    def __init__(
        self,
        fn: Callable[..., Any],
        spec: ToolSpec,
        *,
        lazy: bool = False,
    ) -> None:
        self._fn = fn
        self.spec = spec
        self.is_async = inspect.iscoroutinefunction(fn)
        self._signature = inspect.signature(fn)
        self._validator = build_validator(fn)
        self._context_param = detect_context_param(fn)
        single = get_single_model(fn)
        self._single_model_param: str | None = single[0] if single is not None else None
        self._lazy = lazy
        self._canonical_schema: dict[str, Any] | None = None
        self._provider_schemas: dict[str, dict[str, Any]] = {}
        self._schema_override: Callable[[], dict[str, Any]] | None = None

        functools.update_wrapper(self, fn)

    def __call__(self, *args: Any, **kwargs: Any) -> Any:
        try:
            bound = self._signature.bind_partial(*args, **kwargs)
        except TypeError as exc:
            raise ToolValidationError(str(exc), details={}) from exc

        bound_args = dict(bound.arguments)
        passthrough_context = (
            bound_args.pop(self._context_param, None) if self._context_param else None
        )
        validated = self._validator(bound_args)

        if passthrough_context is not None:
            validated[self._context_param] = passthrough_context  # type: ignore[index]

        if self.is_async:
            return self._invoke_async(validated)

        return self._invoke_sync(validated)

    def invoke(
        self,
        args: dict[str, Any] | None = None,
        *,
        context: Context | None = None,
    ) -> Any:
        """Validate ``args`` and execute the tool, injecting ``context`` by type.

        Intended for runtime use: ``args`` is the LLM-provided argument dict
        (Context is **not** in it), and ``context`` is the runtime context.
        For sync tools returns the value; for async tools returns a coroutine.
        """
        raw = dict(args) if args else {}

        if self._single_model_param is not None:
            raw = {self._single_model_param: raw}

        validated = self._validator(raw)

        if self._context_param is not None and context is not None:
            validated[self._context_param] = context

        if self.is_async:
            return self._invoke_async(validated)

        return self._invoke_sync(validated)

    def _invoke_sync(self, validated: dict[str, Any]) -> Any:
        try:
            return self._fn(**validated)
        except ToolError:
            raise
        except Exception as exc:
            mapped = auto_map_exception(exc)

            if mapped is not None:
                raise mapped from exc

            raise

    async def _invoke_async(self, validated: dict[str, Any]) -> Any:
        try:
            return await self._fn(**validated)
        except ToolError:
            raise
        except Exception as exc:
            mapped = auto_map_exception(exc)

            if mapped is not None:
                raise mapped from exc

            raise

    def get_schema(self, provider: str | None = None) -> dict[str, Any]:
        """Return the JSON schema describing this tool's inputs.

        Without ``provider`` returns the canonical schema, generated lazily
        the first time when the tool was created with ``lazy=True``. With
        ``provider`` returns the adapted schema for that provider, cached
        on first use. Unknown providers raise
        :class:`UnsupportedProviderError`.
        """
        if self._canonical_schema is None:
            if self._schema_override is not None:
                self._canonical_schema = self._schema_override()
            else:
                self._canonical_schema = build_canonical_schema(self._fn)

        if provider is None:
            return self._canonical_schema

        cached = self._provider_schemas.get(provider)

        if cached is not None:
            return cached

        from phronesis.tools.providers import get_adapter

        adapter = get_adapter(provider)
        adapted = adapter.adapt(self._canonical_schema, spec=self.spec)
        self._provider_schemas[provider] = adapted

        return adapted

    def schema(
        self,
        factory: Callable[[], dict[str, Any]],
    ) -> Callable[[], dict[str, Any]]:
        """Register an explicit schema factory, overriding the canonical one.

        Use as a paired decorator on the tool (see ``docs/TOOLS-DECISIONS.md``,
        D-19) for the rare cases where the auto-generated schema is not
        expressive enough. The validator is **not** replaced: overrides are
        purely presentational for the LLM. Any cached schemas (canonical and
        provider-adapted) are invalidated so the new override takes effect
        immediately.
        """
        self._schema_override = factory
        self._canonical_schema = None
        self._provider_schemas.clear()

        return factory

    def __repr__(self) -> str:
        return f"Tool(id={self.spec.id.canonical!r}, name={str(self.spec.name)!r})"
