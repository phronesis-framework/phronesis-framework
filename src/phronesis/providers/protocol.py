"""Provider protocol and capability enum.

:class:`ProviderFeature` is a closed :class:`enum.StrEnum`; adding a
capability requires extending the enum, which forces explicit
coordination across providers and prevents callers from inventing
ad-hoc feature names.

:class:`LLMProvider` is a :class:`typing.Protocol`. Custom providers
satisfy it by structural typing — there is no base class to inherit
from. Built-in providers reuse code via composition, not inheritance.
"""

from __future__ import annotations

from collections.abc import AsyncIterator
from enum import StrEnum
from typing import Protocol, runtime_checkable

from phronesis.providers.chunks import LLMChunk
from phronesis.providers.types import LLMRequest, LLMResponse


class ProviderFeature(StrEnum):
    """Optional capabilities a provider may declare.

    Members are queried via :meth:`LLMProvider.supports` so callers
    can guard provider-specific code paths without hard-coding the
    vendor name.

    Attributes:
        STRUCTURED_OUTPUT: Provider can return values that match a
            caller-supplied schema.
        PROMPT_CACHING: Provider supports caching of large prompt
            prefixes across requests.
        VISION: Provider accepts image inputs alongside text.
        DOCUMENTS: Provider accepts document inputs (PDF, etc).
        EXTENDED_THINKING: Provider exposes a long-form reasoning
            mode billed and returned separately from the answer.
        REASONING_EFFORT: Provider accepts a per-request reasoning
            effort knob.
        PREDICTED_OUTPUTS: Provider supports passing a draft of the
            expected output to accelerate decoding.
    """

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

    A provider is any object exposing :meth:`complete`,
    :meth:`stream` and :meth:`supports`. Built-in providers are
    instantiated via factory functions; custom providers implement
    this protocol directly. The :func:`runtime_checkable` decorator
    enables ``isinstance`` checks against the protocol when needed.
    """

    async def complete(self, request: LLMRequest) -> LLMResponse:
        """Send ``request`` and await the full response.

        Args:
            request: The :class:`LLMRequest` to dispatch.

        Returns:
            The provider's :class:`LLMResponse` carrying messages,
            tool calls and token accounting.
        """
        ...

    def stream(self, request: LLMRequest) -> AsyncIterator[LLMChunk]:
        """Send ``request`` and return an async iterator of chunks.

        Args:
            request: The :class:`LLMRequest` to dispatch.

        Returns:
            An async iterator yielding :data:`LLMChunk` events as
            they arrive from the provider.
        """
        ...

    def supports(self, feature: ProviderFeature) -> bool:
        """Report whether the provider supports ``feature``.

        Args:
            feature: The :class:`ProviderFeature` to probe.

        Returns:
            ``True`` when the provider implements the capability,
            ``False`` otherwise.
        """
        ...
