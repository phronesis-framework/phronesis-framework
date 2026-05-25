"""Convert phronesis :class:`ToolSpec` instances to Anthropic tool format.

Anthropic accepts a ``tools`` array on requests; each entry is an object
with ``name``, optional ``description`` and ``input_schema`` (a JSON
schema). Reference:
https://docs.anthropic.com/en/docs/build-with-claude/tool-use
"""

from __future__ import annotations

from collections.abc import Sequence
from typing import Any

from phronesis.tools import ToolSpec


def to_anthropic_tool(spec: ToolSpec) -> dict[str, Any]:
    """Translate a single :class:`ToolSpec` into the Anthropic shape."""
    tool: dict[str, Any] = {
        "name": str(spec.name),
        "input_schema": dict(spec.input_schema),
    }

    if spec.description:
        tool["description"] = spec.description

    return tool


def to_anthropic_tools(specs: Sequence[ToolSpec]) -> list[dict[str, Any]]:
    """Translate a sequence of :class:`ToolSpec` instances."""
    return [to_anthropic_tool(spec) for spec in specs]
