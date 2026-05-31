"""OpenAI Chat Completions schema adapter.

Produces the
``{type: "function", function: {name, description, parameters}}``
shape consumed by the Chat Completions tool definitions list. The
canonical schema is copied (not mutated) and an explicit
``additionalProperties: false`` is set when the source does not
already declare one. The Responses API format is intentionally not
generated here; a separate adapter can be added later if needed.
"""

from __future__ import annotations

from typing import Any, ClassVar

from phronesis.tools.spec import ToolSpec


class OpenAIAdapter:
    """Adapt a canonical schema to OpenAI's Chat Completions tool format.

    Attributes:
        name: Registry key for this adapter (``"openai"``).
    """

    name: ClassVar[str] = "openai"

    def adapt(
        self,
        canonical: dict[str, Any],
        *,
        spec: ToolSpec,
    ) -> dict[str, Any]:
        """Return the OpenAI-shaped tool definition.

        Args:
            canonical: The canonical JSON schema for the tool's
                inputs. Copied before mutation.
            spec: The tool's :class:`ToolSpec`, source of the
                ``name`` and ``description`` fields.

        Returns:
            A dict ready to drop into the ``tools=[...]`` list of a
            Chat Completions API call.
        """
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
