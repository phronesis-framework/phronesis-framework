"""Memory-aware :class:`ContextBuilder` for RAG over vector memory.

:class:`MemoryAwareContextBuilder` embeds the latest user input,
retrieves the top ``k`` matches from a :class:`VectorStore` and
injects them into the prompt as a system message. The injection
position is configurable so the builder composes cleanly with
:class:`phronesis.context.ChainedContextBuilder`.

The builder honours the :class:`ContextBuilder` invariant: it does
**not** consume ``new_input`` (it only reads it to derive a query),
so chained builders downstream still receive it.
"""

from __future__ import annotations

from collections.abc import Callable
from typing import Literal

from phronesis.context.input import BuildInput
from phronesis.core.messages import (
    Message,
    SystemMessage,
    TextBlock,
    UserMessage,
)
from phronesis.memory.obs import (
    BACKEND_IN_MEMORY,
    MEMORY_SEARCH_MIN_SCORE,
    MEMORY_SEARCH_RESULTS,
    MEMORY_SEARCH_TOP_K,
    STORE_TYPE_VECTOR,
    memory_span,
)
from phronesis.memory.scope import MemoryScope
from phronesis.memory.vector.protocol import EmbeddingProvider, VectorStore

InjectionPosition = Literal["before_system", "after_system"]


class MemoryAwareContextBuilder:
    """Retrieve top-k vector matches and inject them into the prompt.

    The builder builds ``[system?, *retrieved?, *history, new_input?]``.
    When ``injection_position`` is ``"before_system"`` the retrieved
    block precedes the system message; otherwise it follows it. The
    history and ``new_input`` are forwarded verbatim.
    """

    def __init__(
        self,
        vector_store: VectorStore,
        embedding_provider: EmbeddingProvider,
        scope: MemoryScope | Callable[[BuildInput], MemoryScope],
        *,
        top_k: int = 5,
        min_score: float = 0.6,
        injection_position: InjectionPosition = "after_system",
        max_injected_chars: int = 4000,
        backend: str = BACKEND_IN_MEMORY,
    ) -> None:
        """Configure the builder.

        Args:
            vector_store: Backend queried at every ``build`` call.
            embedding_provider: Embedder that turns the query string
                into the vector used for similarity search.
            scope: Either a fixed :class:`MemoryScope` or a callable
                that derives one from the current :class:`BuildInput`.
            top_k: Maximum number of items to retrieve.
            min_score: Minimum cosine similarity for an item to be
                included.
            injection_position: ``"before_system"`` or
                ``"after_system"``.
            max_injected_chars: Hard cap on the total characters
                injected. Items are appended in score order and
                truncated when the cap is hit.
            backend: Label for observability spans. Defaults to
                in-memory; pass a different value when wrapping a
                different backend.
        """
        if top_k <= 0:
            raise ValueError("top_k must be a positive integer")

        if max_injected_chars <= 0:
            raise ValueError("max_injected_chars must be a positive integer")

        self._vector_store = vector_store
        self._embedding_provider = embedding_provider
        self._scope = scope
        self._top_k = top_k
        self._min_score = min_score
        self._injection_position = injection_position
        self._max_injected_chars = max_injected_chars
        self._backend = backend

    def _resolve_scope(self, input: BuildInput) -> MemoryScope:
        if callable(self._scope):
            return self._scope(input)

        return self._scope

    def _extract_query(self, input: BuildInput) -> str | None:
        if input.new_input is not None:
            return _text_of(input.new_input)

        for message in reversed(input.history):
            if isinstance(message, UserMessage):
                return _text_of(message)

        return None

    async def build(self, input: BuildInput) -> list[Message]:
        """Retrieve, inject and return the next message list."""
        scope = self._resolve_scope(input)
        query = self._extract_query(input)
        injected: list[Message] = []

        async with memory_span(
            "context_recall",
            store_type=STORE_TYPE_VECTOR,
            backend=self._backend,
            scope=scope,
            extra={
                MEMORY_SEARCH_TOP_K: self._top_k,
                MEMORY_SEARCH_MIN_SCORE: self._min_score,
            },
        ) as span:
            if query:
                embeddings = await self._embedding_provider.embed((query,))
                results = await self._vector_store.search(
                    scope,
                    embeddings[0],
                    k=self._top_k,
                    min_score=self._min_score,
                )
                span.set_attribute(MEMORY_SEARCH_RESULTS, len(results))
                injected = self._render(results)

        messages: list[Message] = []
        history_starts_with_system = bool(input.history) and isinstance(
            input.history[0], SystemMessage
        )

        if self._injection_position == "before_system":
            messages.extend(injected)

            if input.system_prompt and not history_starts_with_system:
                messages.append(SystemMessage(content=(TextBlock(text=input.system_prompt),)))
        else:
            if input.system_prompt and not history_starts_with_system:
                messages.append(SystemMessage(content=(TextBlock(text=input.system_prompt),)))

            messages.extend(injected)

        messages.extend(input.history)

        if input.new_input is not None:
            messages.append(input.new_input)

        return messages

    def _render(
        self,
        results: tuple[tuple[object, float], ...],
    ) -> list[Message]:
        if not results:
            return []

        snippets: list[str] = []
        used = 0
        budget = self._max_injected_chars

        for item, score in results:
            text = getattr(item, "text", "")
            snippet = f"[score={score:.3f}] {text}"
            remaining = budget - used

            if remaining <= 0:
                break

            if len(snippet) > remaining:
                snippets.append(snippet[:remaining])
                break

            snippets.append(snippet)
            used += len(snippet)

        body = "Relevant context retrieved from memory:\n\n" + "\n\n".join(snippets)

        return [SystemMessage(content=(TextBlock(text=body),))]


def _text_of(message: Message) -> str:
    return "".join(getattr(block, "text", "") for block in message.content)
