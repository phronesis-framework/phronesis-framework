"""OpenAI Chat Completions schema adapter.

Produces the ``{type: "function", function: {name, description, parameters}}``
shape consumed by ``client.chat.completions.create(tools=[...])``. The
Responses API format is not generated here; a separate adapter can be
added later if needed.
"""

from __future__ import annotations

from typing import Any, ClassVar

from phronesis.tools.spec import ToolSpec


class OpenAIAdapter:
    """Adapt a canonical schema to OpenAI's Chat Completions tool format."""

    name: ClassVar[str] = "openai"

    def adapt(
        self,
        canonical: dict[str, Any],
        *,
        spec: ToolSpec,
    ) -> dict[str, Any]:
        parameters = dict(canonical)
        parameters.setdefault("additionalProperties", False)

        return {
            "type": "function",
            "function": {
                "name": str(spec.name),
                "description": spec.description,
                "parameters": parameters,
            },
        }
