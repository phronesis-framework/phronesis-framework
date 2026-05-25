"""Provider protocol and capability enum.

:class:`ProviderFeature` is a closed :class:`enum.StrEnum`; adding a
capability requires extending the enum, which forces explicit
coordination across providers.

:class:`LLMProvider` is a :class:`typing.Protocol`. Custom providers
implement it by structural typing — there is no base class to inherit
from. Reuse across built-in providers happens by composition.
"""

from __future__ import annotations

from collections.abc import AsyncIterator
from enum import StrEnum
from typing import Protocol, runtime_checkable

from phronesis.providers.chunks import LLMChunk
from phronesis.providers.types import LLMRequest, LLMResponse


class ProviderFeature(StrEnum):
    """Optional capabilities a provider may declare via :meth:`LLMProvider.supports`."""

    STRUCTURED_OUTPUT = "structured_output"
    PROMPT_CACHING = "prompt_caching"
    VISION = "vision"
    DOCUMENTS = "documents"
    EXTENDED_THINKING = "extended_thinking"
    REASONING_EFFORT = "reasoning_effort"
    PREDICTED_OUTPUTS = "predicted_outputs"


@runtime_checkable
class LLMProvider(Protocol):
    """Structural contract every provider satisfies.

    A provider is anything exposing ``complete``, ``stream`` and
    ``supports``. Built-in providers are instantiated via factory
    functions; custom providers implement this protocol directly.
    """

    async def complete(self, request: LLMRequest) -> LLMResponse:
        """Send ``request`` and await the full response."""
        ...

    def stream(self, request: LLMRequest) -> AsyncIterator[LLMChunk]:
        """Send ``request`` and return an async iterator of chunks."""
        ...

    def supports(self, feature: ProviderFeature) -> bool:
        """Report whether the provider supports ``feature``."""
        ...
