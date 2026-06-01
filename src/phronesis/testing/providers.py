"""Test-only :class:`LLMProvider` implementations.

These providers never touch the network. They are designed to make
unit tests of agent and tool code fast, deterministic and free of
external dependencies.
"""

from __future__ import annotations

from collections import deque
from collections.abc import AsyncIterator, Iterable, Sequence

from phronesis.core.messages import Message
from phronesis.providers.chunks import LLMChunk
from phronesis.providers.protocol import ProviderFeature
from phronesis.providers.types import LLMRequest, LLMResponse


class FakeProvider:
    """Provider that always returns the same :class:`LLMResponse`.

    Useful for tests where the assertion is about the agent's behaviour
    *given* a model output, not about provider negotiation.

    Attributes:
        response: The :class:`LLMResponse` returned by every call to
            :meth:`complete`.
        calls: Tuple of :class:`LLMRequest` objects received so far,
            in arrival order. Useful for asserting that the agent
            sent the expected prompt.
    """

    __slots__ = ("_calls", "_context_window", "response")

    def __init__(
        self,
        response: LLMResponse | None = None,
        *,
        context_window: int = 200_000,
    ) -> None:
        """Build a :class:`FakeProvider`.

        Args:
            response: Optional canned :class:`LLMResponse`. Defaults
                to a plain ``"done"`` text response with ``"stop"`` as
                its finish reason.
            context_window: Value returned by
                :meth:`context_window_size`. Defaults to ``200_000``.
        """
        self.response = response or LLMResponse(text="done", finish_reason="stop")
        self._calls: list[LLMRequest] = []
        self._context_window = context_window

    @property
    def calls(self) -> tuple[LLMRequest, ...]:
        """Snapshot of every request received, in arrival order."""
        return tuple(self._calls)

    async def complete(self, request: LLMRequest) -> LLMResponse:
        self._calls.append(request)

        return self.response

    def stream(self, request: LLMRequest) -> AsyncIterator[LLMChunk]:
        async def _empty() -> AsyncIterator[LLMChunk]:
            return
            yield  # pragma: no cover - empty async generator

        return _empty()

    def supports(self, feature: ProviderFeature) -> bool:
        return False

    def context_window_size(self) -> int:
        return self._context_window

    def count_tokens(self, messages: Sequence[Message]) -> int:
        return 0


class ScriptedProvider:
    """Provider that pops one :class:`LLMResponse` per call from a queue.

    Each call to :meth:`complete` consumes the next response in the
    script. When the script is exhausted, :class:`IndexError` is
    raised so tests fail loudly instead of silently re-using the
    last response.

    Attributes:
        calls: Tuple of :class:`LLMRequest` objects received so far,
            in arrival order.
        remaining: Number of responses still queued.
    """

    __slots__ = ("_calls", "_context_window", "_responses")

    def __init__(
        self,
        responses: Iterable[LLMResponse],
        *,
        context_window: int = 200_000,
    ) -> None:
        """Build a :class:`ScriptedProvider`.

        Args:
            responses: Iterable of :class:`LLMResponse` instances,
                consumed in order. The iterable is materialised at
                construction time.
            context_window: Value returned by
                :meth:`context_window_size`. Defaults to ``200_000``.
        """
        self._responses: deque[LLMResponse] = deque(responses)
        self._calls: list[LLMRequest] = []
        self._context_window = context_window

    @property
    def calls(self) -> tuple[LLMRequest, ...]:
        """Snapshot of every request received, in arrival order."""
        return tuple(self._calls)

    @property
    def remaining(self) -> int:
        """Number of responses still queued."""
        return len(self._responses)

    async def complete(self, request: LLMRequest) -> LLMResponse:
        if not self._responses:
            raise IndexError(
                "ScriptedProvider exhausted: no scripted response left "
                f"for request #{len(self._calls) + 1}",
            )

        self._calls.append(request)

        return self._responses.popleft()

    def stream(self, request: LLMRequest) -> AsyncIterator[LLMChunk]:
        async def _empty() -> AsyncIterator[LLMChunk]:
            return
            yield  # pragma: no cover - empty async generator

        return _empty()

    def supports(self, feature: ProviderFeature) -> bool:
        return False

    def context_window_size(self) -> int:
        return self._context_window

    def count_tokens(self, messages: Sequence[Message]) -> int:
        return 0
