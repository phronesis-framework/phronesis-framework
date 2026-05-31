"""Anthropic Messages API schema adapter.

Produces the ``{name, description, input_schema}`` shape consumed
directly by the Messages API tool definitions list. The canonical
schema is copied (not mutated) and an explicit
``additionalProperties: false`` is set when the source does not
already declare one, so the model cannot smuggle extra keys past the
validator.
"""

from __future__ import annotations

from typing import Any, ClassVar

from phronesis.tools.spec import ToolSpec


class AnthropicAdapter:
    """Adapt a canonical schema to Anthropic's Messages API tool format.

    Attributes:
        name: Registry key for this adapter (``"anthropic"``).
    """

    name: ClassVar[str] = "anthropic"

    def adapt(
        self,
        canonical: dict[str, Any],
        *,
        spec: ToolSpec,
    ) -> dict[str, Any]:
        """Return the Anthropic-shaped tool definition.

        Args:
            canonical: The canonical JSON schema for the tool's
                inputs. Copied before mutation.
            spec: The tool's :class:`ToolSpec`, source of the
                ``name`` and ``description`` fields.

        Returns:
            A dict ready to drop into the ``tools=[...]`` list of an
            Anthropic Messages API call.
        """
        input_schema = dict(canonical)
        input_schema.setdefault("additionalProperties", False)

        return {
            "name": str(spec.name),
            "description": spec.description,
            "input_schema": input_schema,
        }
