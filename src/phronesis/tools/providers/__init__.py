"""Provider adapter registry.

A small, closed dictionary maps provider names (``"anthropic"``,
``"openai"``, ...) to adapter instances that adapt the canonical
JSON schema into the shape each provider expects. The registry is
intentionally closed: new providers are added by extending this
module, not by user-side registration calls. Looking up an unknown
name raises :class:`UnsupportedProviderError`.
"""

from __future__ import annotations

from phronesis.tools.errors import UnsupportedProviderError
from phronesis.tools.providers.anthropic import AnthropicAdapter
from phronesis.tools.providers.base import ProviderAdapter
from phronesis.tools.providers.openai import OpenAIAdapter

_ADAPTERS: dict[str, ProviderAdapter] = {
    AnthropicAdapter.name: AnthropicAdapter(),
    OpenAIAdapter.name: OpenAIAdapter(),
}


def get_adapter(name: str) -> ProviderAdapter:
    """Return the adapter registered under ``name``.

    Args:
        name: Provider identifier (``"anthropic"``, ``"openai"``, ...).

    Returns:
        The :class:`ProviderAdapter` instance bound to that name.

    Raises:
        UnsupportedProviderError: when no adapter is registered for
            ``name``. The error ``details`` payload lists the
            currently available providers so callers can recover.
    """
    try:
        return _ADAPTERS[name]
    except KeyError as exc:
        raise UnsupportedProviderError(
            f"No adapter registered for provider {name!r}",
            details={"provider": name, "available": sorted(_ADAPTERS)},
        ) from exc


__all__ = ["ProviderAdapter", "get_adapter"]
