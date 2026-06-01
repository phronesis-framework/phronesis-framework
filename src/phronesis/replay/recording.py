"""Recording proxy that captures provider responses to a cassette.

:class:`RecordingProvider` wraps any :class:`LLMProvider`, forwards
``complete`` and ``stream`` to the inner provider, and appends each
:class:`LLMResponse` from ``complete`` to a JSONL cassette on disk.

Streaming is not recorded in the MVP: ``stream`` falls through to the
inner provider unchanged so existing streaming agents keep working,
but the cassette will contain no entries for those calls. Replay of
streaming runs is therefore unsupported by :class:`ReplayProvider`.
"""

from __future__ import annotations

from collections.abc import AsyncIterator, Sequence
from pathlib import Path

from phronesis.core.messages import Message
from phronesis.providers.chunks import LLMChunk
from phronesis.providers.protocol import LLMProvider, ProviderFeature
from phronesis.providers.types import LLMRequest, LLMResponse
from phronesis.replay.cassette import append_cassette


class RecordingProvider:
    """Provider proxy that appends every completion to a cassette file.

    The cassette is opened in append mode for each call, so partial
    progress survives crashes. The file is truncated on construction
    when ``truncate=True``.
    """

    def __init__(
        self,
        inner: LLMProvider,
        cassette_path: str | Path,
        *,
        truncate: bool = True,
    ) -> None:
        """Wrap ``inner`` and target ``cassette_path``.

        Args:
            inner: The real provider whose responses will be recorded.
            cassette_path: Filesystem path for the JSONL cassette.
            truncate: When ``True`` (default), clears the cassette on
                construction so a new recording does not concatenate
                with stale entries.
        """
        self._inner = inner
        self._path = Path(cassette_path)

        if truncate:
            self._path.parent.mkdir(parents=True, exist_ok=True)
            self._path.write_text("", encoding="utf-8")

    async def complete(self, request: LLMRequest) -> LLMResponse:
        """Forward ``request`` and append the response to the cassette."""
        response = await self._inner.complete(request)

        append_cassette(self._path, response)

        return response

    def stream(self, request: LLMRequest) -> AsyncIterator[LLMChunk]:
        """Stream from the inner provider unchanged. Not recorded."""
        return self._inner.stream(request)

    def supports(self, feature: ProviderFeature) -> bool:
        """Mirror the inner provider's capability set."""
        return self._inner.supports(feature)

    def context_window_size(self) -> int:
        """Mirror the inner provider's context window size."""
        return self._inner.context_window_size()

    def count_tokens(self, messages: Sequence[Message]) -> int:
        """Mirror the inner provider's token counter."""
        return self._inner.count_tokens(messages)

    async def count_tokens_exact(self, messages: Sequence[Message]) -> int | None:
        """Mirror the inner provider's exact token counter."""
        return await self._inner.count_tokens_exact(messages)
