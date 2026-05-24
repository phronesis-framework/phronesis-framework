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

from phronesis.tools.errors import ToolError, ToolValidationError, auto_map_exception
from phronesis.tools.schema import build_canonical_schema
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
        self._lazy = lazy
        self._canonical_schema: dict[str, Any] | None = None

        functools.update_wrapper(self, fn)

    def __call__(self, *args: Any, **kwargs: Any) -> Any:
        try:
            bound = self._signature.bind_partial(*args, **kwargs)
        except TypeError as exc:
            raise ToolValidationError(str(exc), details={}) from exc

        validated = self._validator(dict(bound.arguments))

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
        the first time when the tool was created with ``lazy=True``. Per
        D-25 the dict is returned raw.
        """
        if provider is not None:
            raise NotImplementedError(
                "Provider-specific schemas are not implemented yet (FASE 7).",
            )

        if self._canonical_schema is None:
            self._canonical_schema = build_canonical_schema(self._fn)

        return self._canonical_schema

    def __repr__(self) -> str:
        return f"Tool(id={self.spec.id.canonical!r}, name={str(self.spec.name)!r})"
