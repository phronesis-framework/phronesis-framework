"""Tool spec conversion for the OpenAI provider.

The Chat Completions API wraps each tool inside a
``{"type": "function", "function": {...}}`` envelope. The inner
``function`` object holds ``name``, optional ``description`` and
``parameters`` (a JSON Schema). These helpers translate the
framework's :class:`ToolSpec` into that shape, dropping the
description key when the spec has none.
"""

from __future__ import annotations

from collections.abc import Iterable
from typing import Any

from phronesis.tools import ToolSpec


def to_openai_tool(spec: ToolSpec) -> dict[str, Any]:
    """Convert a single :class:`ToolSpec` to an OpenAI tool dict.

    Args:
        spec: The tool spec to translate. Its ``input_schema`` is
            copied to avoid sharing the mapping with the caller.

    Returns:
        A dict ready to drop into a Chat Completions ``tools`` array.
    """
    function: dict[str, Any] = {
        "name": str(spec.name),
        "parameters": dict(spec.input_schema),
    }

    if spec.description:
        function["description"] = spec.description

    return {"type": "function", "function": function}


def to_openai_tools(specs: Iterable[ToolSpec]) -> list[dict[str, Any]]:
    """Convert a sequence of :class:`ToolSpec` to OpenAI tool dicts.

    Args:
        specs: Tool specs to translate. The iteration order is
            preserved.

    Returns:
        A list of dicts in the order of ``specs``.
    """
    return [to_openai_tool(spec) for spec in specs]
