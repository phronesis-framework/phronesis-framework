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

from phronesis.tools.errors import ToolValidationError
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

    def __init__(self, fn: Callable[..., Any], spec: ToolSpec) -> None:
        self._fn = fn
        self.spec = spec
        self.is_async = inspect.iscoroutinefunction(fn)
        self._signature = inspect.signature(fn)
        self._validator = build_validator(fn)

        functools.update_wrapper(self, fn)

    def __call__(self, *args: Any, **kwargs: Any) -> Any:
        try:
            bound = self._signature.bind_partial(*args, **kwargs)
        except TypeError as exc:
            raise ToolValidationError(str(exc), details={}) from exc

        validated = self._validator(dict(bound.arguments))

        return self._fn(**validated)

    def __repr__(self) -> str:
        return f"Tool(id={self.spec.id.canonical!r}, name={str(self.spec.name)!r})"
