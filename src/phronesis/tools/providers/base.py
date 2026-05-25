"""``ProviderAdapter`` Protocol — contract for provider-specific schemas.

A single canonical input schema is generated eagerly per tool. Adapters
translate that canonical schema to each provider's expected shape lazily,
on the first call to :meth:`Tool.get_schema(provider=...)`, and the
result is cached per ``(tool, provider)`` pair.
"""

from __future__ import annotations

from typing import Any, ClassVar, Protocol, runtime_checkable

from phronesis.tools.spec import ToolSpec


@runtime_checkable
class ProviderAdapter(Protocol):
    """Translate a canonical input schema into a provider-shaped tool definition.

    Implementations must be deterministic and side-effect-free: ``adapt``
    is called once per ``(tool, provider)`` pair and its result is cached.
    """

    name: ClassVar[str]

    def adapt(
        self,
        canonical: dict[str, Any],
        *,
        spec: ToolSpec,
    ) -> dict[str, Any]:
        """Return the provider's tool definition built from ``canonical`` and ``spec``."""
        ...
