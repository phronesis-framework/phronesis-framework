"""Replay provider that returns cassette entries instead of calling a real API.

:class:`ReplayProvider` reads a JSONL cassette eagerly on construction
and serves :class:`LLMResponse` values in order on each ``complete``
call. Streaming is not supported in the MVP.

The replay provider does not call out to the network, so it is safe
to use in tests and CI without any vendor credentials. The response
sequence is opaque: there is no request validation. Callers that need
strict request matching should wrap the cassette themselves.
"""

from __future__ import annotations

from collections.abc import AsyncIterator, Sequence
from pathlib import Path

from phronesis.core.messages import Message
from phronesis.providers.chunks import LLMChunk
from phronesis.providers.protocol import ProviderFeature
from phronesis.providers.types import LLMRequest, LLMResponse
from phronesis.replay.cassette import read_cassette
from phronesis.replay.errors import CassetteExhaustedError


class ReplayProvider:
    """Provider that serves recorded :class:`LLMResponse` values in order.

    Construction reads the cassette from disk and stores responses in
    memory. Each :meth:`complete` returns the next entry and advances
    an internal cursor. Asking for more responses than were recorded
    raises :class:`CassetteExhaustedError`.
    """

    def __init__(
        self,
        cassette_path: str | Path,
        *,
        context_window: int = 200_000,
    ) -> None:
        """Load ``cassette_path`` into memory.

        Args:
            cassette_path: Filesystem path to the JSONL cassette.
            context_window: Synthetic context window reported by
                :meth:`context_window_size`. The replay provider has
                no real model, so callers pick a value compatible
                with the original recording when they need
                :class:`CompactingContextBuilder` to behave the same.

        Raises:
            CassetteFormatError: when ``cassette_path`` is missing or
                contains malformed entries.
        """
        self._responses = read_cassette(Path(cassette_path))
        self._cursor = 0
        self._context_window = context_window

    async def complete(self, request: LLMRequest) -> LLMResponse:
        """Return the next recorded response.

        Raises:
            CassetteExhaustedError: when the cassette has no more
                entries left.
        """
        if self._cursor >= len(self._responses):
            raise CassetteExhaustedError(
                "ReplayProvider has no more responses recorded.",
                details={"recorded": len(self._responses)},
            )

        response = self._responses[self._cursor]
        self._cursor += 1

        return response

    def stream(self, request: LLMRequest) -> AsyncIterator[LLMChunk]:
        """Streaming is not supported by the replay provider."""

        async def _empty() -> AsyncIterator[LLMChunk]:
            raise CassetteExhaustedError("ReplayProvider does not support streaming.")
            yield  # pragma: no cover

        return _empty()

    def supports(self, feature: ProviderFeature) -> bool:
        """Return ``False`` for every feature. Replay carries no native capabilities."""
        return False

    def context_window_size(self) -> int:
        """Return the synthetic context window supplied at construction."""
        return self._context_window

    def count_tokens(self, messages: Sequence[Message]) -> int:
        """Estimate token count via the canonical 4-chars-per-token heuristic.

        Sums the length of textual representations of every content
        block. Best-effort and not meant for billing.
        """
        total_chars = 0

        for message in messages:
            for block in message.content:
                total_chars += len(str(getattr(block, "text", ""))) + len(
                    str(getattr(block, "tool_name", ""))
                )

        return total_chars // 4

    async def count_tokens_exact(self, messages: Sequence[Message]) -> int | None:
        """Return ``None``. Replay has no native token counter."""
        return None
