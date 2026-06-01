"""Multi-provider fallback wrapper.

:class:`FallbackProvider` composes an ordered sequence of
:class:`LLMProvider` instances into a single provider. ``complete``
tries each provider in order and returns the first successful
response. If a provider raises an exception in the configured
``fallback_on`` set, the wrapper proceeds to the next one. When every
provider fails the wrapper raises :class:`FallbackExhaustedError`
carrying the last exception as its ``__cause__``.

``stream`` follows the same policy on a best-effort basis: the
wrapper falls back only if creating the iterator or pulling the
**first** chunk raises a fallback error. After any chunk has been
yielded, mid-stream exceptions propagate to the caller unchanged
because there is no safe way to restart the stream from another
provider once tokens have been emitted.

Capability and accounting methods (``supports``,
``context_window_size``, ``count_tokens``, ``count_tokens_exact``)
delegate to the **first** provider in the list. The list is treated
as ordered preference, so the first entry is the authoritative source
for capabilities — callers should put their preferred provider first.
"""

from __future__ import annotations

from collections.abc import AsyncIterator, Sequence
from typing import TYPE_CHECKING

from phronesis.providers.chunks import LLMChunk
from phronesis.providers.errors import ProviderError
from phronesis.providers.protocol import LLMProvider, ProviderFeature
from phronesis.providers.types import LLMRequest, LLMResponse

if TYPE_CHECKING:
    from phronesis.core.messages import Message


class FallbackExhaustedError(ProviderError):
    """Every provider in the fallback chain failed.

    The last raised exception is attached as ``__cause__`` so callers
    can introspect the underlying failure.
    """


class FallbackProvider:
    """Compose multiple :class:`LLMProvider` instances into a chain.

    Attributes are read-only after construction. The wrapper itself
    satisfies :class:`LLMProvider` so it can be used anywhere a
    single provider is expected (including inside ``apply_middleware``
    or as the inner of a :class:`phronesis.replay.RecordingProvider`).
    """

    def __init__(
        self,
        providers: Sequence[LLMProvider],
        *,
        fallback_on: tuple[type[BaseException], ...] = (ProviderError,),
    ) -> None:
        """Build the wrapper.

        Args:
            providers: Ordered sequence of providers. Must contain at
                least one element. The first entry is tried first and
                also serves as the authoritative source for capability
                queries.
            fallback_on: Tuple of exception classes that trigger a
                fallback to the next provider. Defaults to the whole
                :class:`ProviderError` family so transient remote
                failures (rate-limit, transport, 5xx) all roll over.

        Raises:
            ValueError: If ``providers`` is empty.
        """
        if not providers:
            raise ValueError("FallbackProvider requires at least one provider")

        self._providers: tuple[LLMProvider, ...] = tuple(providers)
        self._fallback_on = fallback_on

    async def complete(self, request: LLMRequest) -> LLMResponse:
        """Try each provider in order until one returns a response."""
        last_exc: BaseException | None = None

        for provider in self._providers:
            try:
                return await provider.complete(request)
            except self._fallback_on as exc:
                last_exc = exc

        raise FallbackExhaustedError(
            f"All {len(self._providers)} providers failed",
        ) from last_exc

    def stream(self, request: LLMRequest) -> AsyncIterator[LLMChunk]:
        """Return a chunk iterator backed by the first usable provider.

        Falls back only until the **first** chunk arrives; once any
        chunk has been yielded, the underlying iterator is responsible
        for the rest of the stream and errors propagate unchanged.
        """
        return self._stream_with_fallback(request)

    async def _stream_with_fallback(self, request: LLMRequest) -> AsyncIterator[LLMChunk]:
        last_exc: BaseException | None = None

        for provider in self._providers:
            try:
                iterator = provider.stream(request).__aiter__()
                first_chunk = await iterator.__anext__()
            except StopAsyncIteration:
                return
            except self._fallback_on as exc:
                last_exc = exc

                continue

            yield first_chunk

            async for chunk in iterator:
                yield chunk

            return

        raise FallbackExhaustedError(
            f"All {len(self._providers)} providers failed to stream",
        ) from last_exc

    def supports(self, feature: ProviderFeature) -> bool:
        """Mirror the first provider's capability set."""
        return self._providers[0].supports(feature)

    def context_window_size(self) -> int:
        """Mirror the first provider's context window size."""
        return self._providers[0].context_window_size()

    def count_tokens(self, messages: Sequence[Message]) -> int:
        """Mirror the first provider's token counter."""
        return self._providers[0].count_tokens(messages)

    async def count_tokens_exact(self, messages: Sequence[Message]) -> int | None:
        """Mirror the first provider's exact token counter."""
        return await self._providers[0].count_tokens_exact(messages)
