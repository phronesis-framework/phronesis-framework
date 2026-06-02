"""``ProviderAdapter`` Protocol — contract for provider-specific schemas.

A single canonical schema is generated eagerly per tool; adapters
translate it to each provider's expected shape lazily, on the first
call to :meth:`Tool.get_schema(provider=...)`. The translated
schemas are cached on the :class:`Tool` instance so subsequent calls
return the same dict without re-running the adapter.
"""

from __future__ import annotations

from typing import Any, ClassVar, Protocol, runtime_checkable

from phronesis.tools.spec import ToolSpec


@runtime_checkable
class ProviderAdapter(Protocol):
    """Translate a canonical input schema into a provider-shaped tool definition.

    Implementations must be deterministic and side-effect-free:
    ``adapt`` is called at most once per ``(tool, provider)`` pair
    and its result is cached on the tool. Adapters are looked up by
    the :attr:`name` class variable.

    Attributes:
        name: Stable provider identifier (e.g. ``"anthropic"``,
            ``"openai"``). Used as the key into the adapter registry.
    """

    name: ClassVar[str]

    def adapt(
        self,
        canonical: dict[str, Any],
        *,
        spec: ToolSpec,
    ) -> dict[str, Any]:
        """Build the provider's tool definition from ``canonical`` and ``spec``.

        Args:
            canonical: The canonical JSON schema describing the
                tool's inputs.
            spec: The pure-data :class:`ToolSpec` of the tool, used
                to fill in provider-side metadata (name,
                description, ...).

        Returns:
            The provider-shaped tool definition dict, ready to be
            sent to the LLM in the tool-definitions list.
        """
        ...
