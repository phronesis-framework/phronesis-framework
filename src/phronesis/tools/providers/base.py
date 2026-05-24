"""``ProviderAdapter`` Protocol — contract for provider-specific schemas.

See ``docs/TOOLS-DECISIONS.md`` (D-23, D-24): a single canonical schema is
generated eagerly per tool; adapters translate it to each provider's
expected shape lazily, on the first call to
:meth:`Tool.get_schema(provider=...)`.
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
