"""Anthropic Messages API schema adapter.

Produces the ``{name, description, input_schema}`` shape consumed directly
by ``client.messages.create(tools=[...])``.
"""

from __future__ import annotations

from typing import Any, ClassVar

from phronesis.tools.spec import ToolSpec


class AnthropicAdapter:
    """Adapt a canonical schema to Anthropic's Messages API tool format."""

    name: ClassVar[str] = "anthropic"

    def adapt(
        self,
        canonical: dict[str, Any],
        *,
        spec: ToolSpec,
    ) -> dict[str, Any]:
        input_schema = dict(canonical)
        input_schema.setdefault("additionalProperties", False)

        return {
            "name": str(spec.name),
            "description": spec.description,
            "input_schema": input_schema,
        }
