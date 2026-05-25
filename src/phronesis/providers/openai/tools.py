"""Tool spec conversion for the OpenAI provider.

OpenAI wraps each tool inside a ``{"type": "function", "function": {...}}``
envelope. The inner ``function`` holds ``name``, optional ``description``
and ``parameters`` (a JSON schema).
"""

from __future__ import annotations

from collections.abc import Iterable
from typing import Any

from phronesis.tools import ToolSpec


def to_openai_tool(spec: ToolSpec) -> dict[str, Any]:
    """Convert a single :class:`ToolSpec` to an OpenAI tool dict."""
    function: dict[str, Any] = {
        "name": str(spec.name),
        "parameters": dict(spec.input_schema),
    }

    if spec.description:
        function["description"] = spec.description

    return {"type": "function", "function": function}


def to_openai_tools(specs: Iterable[ToolSpec]) -> list[dict[str, Any]]:
    """Convert a sequence of :class:`ToolSpec` instances."""
    return [to_openai_tool(spec) for spec in specs]
