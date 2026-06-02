"""Convert phronesis :class:`ToolSpec` instances to Anthropic tool format.

The Anthropic API accepts a ``tools`` array on the request; each
entry is an object with ``name``, optional ``description`` and an
``input_schema`` JSON Schema. These helpers translate the
framework's :class:`ToolSpec` (or a sequence of them) into that
shape, dropping the description key when the spec has none.
"""

from __future__ import annotations

from collections.abc import Sequence
from typing import Any

from phronesis.tools import ToolSpec


def to_anthropic_tool(spec: ToolSpec) -> dict[str, Any]:
    """Translate a single :class:`ToolSpec` into the Anthropic shape.

    Args:
        spec: The tool spec to translate. Its ``input_schema`` is
            copied to avoid sharing the mapping with the caller.

    Returns:
        A dict ready to drop into a request's ``tools`` array.
    """
    tool: dict[str, Any] = {
        "name": str(spec.name),
        "input_schema": dict(spec.input_schema),
    }

    if spec.description:
        tool["description"] = spec.description

    return tool


def to_anthropic_tools(specs: Sequence[ToolSpec]) -> list[dict[str, Any]]:
    """Translate a sequence of :class:`ToolSpec` into Anthropic shape.

    Args:
        specs: Tool specs to translate. The order is preserved.

    Returns:
        A list of dicts in the order of ``specs``.
    """
    return [to_anthropic_tool(spec) for spec in specs]
