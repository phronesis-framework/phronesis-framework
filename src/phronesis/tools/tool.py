"""Invocable wrapper that pairs a callable with its :class:`ToolSpec`.

:class:`Tool` is the callable side of a tool declaration; the
pure-data side lives on :attr:`Tool.spec`. Both sync and async
callables are supported transparently via :meth:`Tool.__call__`:

* a sync callable returns the value directly;
* an async callable returns a coroutine that the caller awaits.

The wrapper also owns:

* the dynamic argument validator (built from the function signature
  by :func:`build_validator`);
* the :class:`Context`-parameter name (detected once at construction);
* the optional single-:class:`BaseModel` parameter name;
* the lazily-built canonical JSON schema and its per-provider
  adapted variants.
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

    The instance mirrors :func:`functools.update_wrapper`, so
    ``Tool.__name__`` and ``Tool.__wrapped__`` are the same as the
    underlying function. ``__call__`` delegates to that function and
    handles validation, optional context injection, and exception
    mapping via :func:`auto_map_exception`.

    Attributes:
        spec: The :class:`ToolSpec` describing this tool.
        is_async: ``True`` when the wrapped callable is a coroutine
            function.
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
        """Bind ``fn`` and ``spec`` into a callable tool.

        Args:
            fn: The user-defined function (sync or async) that the
                tool executes.
            spec: The pre-built :class:`ToolSpec` to expose. The
                wrapper does not re-build the spec.
            lazy: When ``True``, the canonical JSON schema is **not**
                computed eagerly here; it will be generated the first
                time :meth:`get_schema` is invoked. When ``False``,
                the decorator passes the pre-computed schema in
                separately via :attr:`_canonical_schema`.
        """
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
        """Validate ``args`` and execute the tool, injecting ``context``.

        The runtime calls this method, not :meth:`__call__`. ``args``
        is the LLM-provided argument dict and must **not** include
        the runtime context — that is supplied via the ``context``
        keyword and is matched to the tool's :class:`Context`-typed
        parameter (if any) by name.

        Single-:class:`BaseModel` tools receive ``args`` wrapped under
        the model's parameter name so pydantic can build the model
        instance in one go.

        Args:
            args: Arguments produced by the model. ``None`` is treated
                as an empty dict.
            context: Runtime :class:`Context` to inject. Ignored when
                the tool does not declare a :class:`Context`
                parameter.

        Returns:
            The return value for sync tools, or an awaitable
            coroutine for async tools.

        Raises:
            ToolValidationError: if ``args`` does not satisfy the
                tool's input schema.
            ToolError: subclasses raised by the tool itself or mapped
                from a standard exception by
                :func:`auto_map_exception`.
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

        The canonical schema is built once per tool instance; the
        per-provider adapted schema is cached on first use.

        Args:
            provider: Provider name (``"anthropic"``, ``"openai"``,
                ...) selecting an adapter. ``None`` returns the raw
                canonical schema.

        Returns:
            The canonical JSON schema, or the provider-adapted
            equivalent when ``provider`` is given.

        Raises:
            UnsupportedProviderError: if ``provider`` is not
                registered in :mod:`phronesis.tools.providers`.
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

        Use as a paired decorator on the tool for the rare cases
        where the auto-generated schema is not expressive enough. The
        argument validator is **not** replaced: overrides are purely
        presentational for the LLM. Any cached schemas (canonical and
        provider-adapted) are invalidated so the new override takes
        effect on the next call.

        Args:
            factory: Zero-argument callable that returns the canonical
                JSON schema dictionary.

        Returns:
            ``factory`` unchanged, so this method can be used as a
            stacked decorator.
        """
        self._schema_override = factory
        self._canonical_schema = None
        self._provider_schemas.clear()

        return factory

    def __repr__(self) -> str:
        return f"Tool(id={self.spec.id.canonical!r}, name={str(self.spec.name)!r})"
