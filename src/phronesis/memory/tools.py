"""Programmatic memory tool factories.

Unlike user-defined tools - which are typically declared with the
:func:`phronesis.tools.decorator.tool` decorator and auto-registered
in the active registry - memory tools are **constructed** by
:func:`make_memory_tools`. The factory returns plain :class:`Tool`
instances which the caller is expected to register inside an explicit
:func:`phronesis.tools.tool_scope` so they do not pollute the global
registry.

The factory builds one tool per available store/embedder. Pass only
the stores the agent needs: missing arguments simply omit the
corresponding tool.
"""

from __future__ import annotations

from collections.abc import Callable, Iterable
from typing import Any

from phronesis.memory.kv.protocol import KeyValueStore
from phronesis.memory.scope import MemoryLevel, MemoryScope
from phronesis.memory.vector.protocol import EmbeddingProvider, VectorStore
from phronesis.memory.working import WorkingMemoryStore
from phronesis.tools.spec import ToolSpec
from phronesis.tools.tool import Tool
from phronesis.tools.tool_id import ToolId, ToolName, tool_id_generator

ScopeResolver = Callable[[str], MemoryScope]
"""Callable that turns a scope-level string into a :class:`MemoryScope`."""


def _default_scope_resolver() -> ScopeResolver:
    """Return a resolver that builds scopes with id ``"_default"``.

    The default resolver is convenient for examples and tests but
    production callers will typically pass a resolver that closes over
    the run's session/agent/run identifiers.
    """

    def resolve(level: str) -> MemoryScope:
        as_level = MemoryLevel(level)

        if as_level is MemoryLevel.GLOBAL:
            return MemoryScope.global_()

        return MemoryScope(level=as_level, id="_default")

    return resolve


def _spec(
    name: str,
    description: str,
    input_schema: dict[str, Any],
) -> ToolSpec:
    canonical = f"phronesis.memory.tools.{name}"
    tool_id: ToolId = tool_id_generator.from_canonical(canonical)

    return ToolSpec(
        id=tool_id,
        name=ToolName(name),
        description=description,
        input_schema=input_schema,
    )


def _string_schema(description: str) -> dict[str, Any]:
    return {"type": "string", "description": description}


def _level_schema() -> dict[str, Any]:
    return {
        "type": "string",
        "enum": [level.value for level in MemoryLevel],
        "description": "Scope level for the operation.",
        "default": "session",
    }


def make_memory_tools(
    *,
    working: WorkingMemoryStore | None = None,
    kv: KeyValueStore | None = None,
    vector: VectorStore | None = None,
    embedding: EmbeddingProvider | None = None,
    scope_resolver: ScopeResolver | None = None,
) -> tuple[Tool, ...]:
    """Build a tuple of memory :class:`Tool` instances for the supplied stores.

    Args:
        working: Optional working store. Enables ``memory_note``.
        kv: Optional KV store. Enables ``memory_remember``,
            ``memory_recall`` and ``memory_forget``.
        vector: Optional vector store. Enables ``memory_search``.
        embedding: Required when ``vector`` is provided; ignored
            otherwise. Used by ``memory_search`` to embed the query.
        scope_resolver: Callable mapping a scope-level string to a
            :class:`MemoryScope`. Defaults to a resolver that builds
            scopes with id ``"_default"``.

    Returns:
        Tuple of :class:`Tool` instances. The caller is responsible
        for registering them inside an explicit
        :func:`phronesis.tools.tool_scope`.

    Raises:
        ValueError: when ``vector`` is provided without ``embedding``.
    """
    if vector is not None and embedding is None:
        raise ValueError("make_memory_tools(vector=...) requires an embedding provider.")

    resolve = scope_resolver if scope_resolver is not None else _default_scope_resolver()
    tools: list[Tool] = []

    if kv is not None:
        tools.append(_build_remember(kv, resolve))
        tools.append(_build_recall(kv, resolve))
        tools.append(_build_forget(kv, resolve))

    if vector is not None and embedding is not None:
        tools.append(_build_search(vector, embedding, resolve))

    if working is not None:
        tools.append(_build_note(working, resolve))

    return tuple(tools)


def _build_remember(kv: KeyValueStore, resolve: ScopeResolver) -> Tool:
    async def memory_remember(
        key: str,
        value: str,
        scope_level: str = "session",
    ) -> dict[str, Any]:
        """Persist a value under ``key`` in the chosen scope."""
        await kv.set(resolve(scope_level), key, value)

        return {"ok": True, "key": key, "scope_level": scope_level}

    spec = _spec(
        "memory_remember",
        "Persist a value under a key in the chosen memory scope.",
        {
            "type": "object",
            "properties": {
                "key": _string_schema("Key to store the value under."),
                "value": _string_schema("Value to persist."),
                "scope_level": _level_schema(),
            },
            "required": ["key", "value"],
        },
    )

    return Tool(memory_remember, spec, lazy=True)


def _build_recall(kv: KeyValueStore, resolve: ScopeResolver) -> Tool:
    async def memory_recall(
        key: str,
        scope_level: str = "session",
    ) -> dict[str, Any]:
        """Return the value stored under ``key`` in the chosen scope."""
        value = await kv.get(resolve(scope_level), key)

        return {"key": key, "value": value, "scope_level": scope_level}

    spec = _spec(
        "memory_recall",
        "Return the value stored under a key in the chosen memory scope.",
        {
            "type": "object",
            "properties": {
                "key": _string_schema("Key to recall."),
                "scope_level": _level_schema(),
            },
            "required": ["key"],
        },
    )

    return Tool(memory_recall, spec, lazy=True)


def _build_forget(kv: KeyValueStore, resolve: ScopeResolver) -> Tool:
    async def memory_forget(
        key: str,
        scope_level: str = "session",
    ) -> dict[str, Any]:
        """Delete the entry under ``key`` in the chosen scope."""
        existed = await kv.delete(resolve(scope_level), key)

        return {"key": key, "deleted": existed, "scope_level": scope_level}

    spec = _spec(
        "memory_forget",
        "Delete the entry under a key in the chosen memory scope.",
        {
            "type": "object",
            "properties": {
                "key": _string_schema("Key to delete."),
                "scope_level": _level_schema(),
            },
            "required": ["key"],
        },
    )

    return Tool(memory_forget, spec, lazy=True)


def _build_search(
    vector: VectorStore,
    embedding: EmbeddingProvider,
    resolve: ScopeResolver,
) -> Tool:
    async def memory_search(
        query: str,
        k: int = 5,
        scope_level: str = "session",
    ) -> dict[str, Any]:
        """Search the vector store for the top ``k`` matches of ``query``."""
        scope = resolve(scope_level)
        embeddings = await embedding.embed((query,))
        results = await vector.search(scope, embeddings[0], k=k)

        return {
            "query": query,
            "scope_level": scope_level,
            "results": [
                {
                    "id": item.id,
                    "text": item.text,
                    "score": score,
                    "metadata": dict(item.metadata),
                }
                for item, score in results
            ],
        }

    spec = _spec(
        "memory_search",
        "Search the vector store for the top-k semantic matches of a query.",
        {
            "type": "object",
            "properties": {
                "query": _string_schema("Text to search for."),
                "k": {
                    "type": "integer",
                    "description": "Maximum number of results.",
                    "default": 5,
                    "minimum": 1,
                },
                "scope_level": _level_schema(),
            },
            "required": ["query"],
        },
    )

    return Tool(memory_search, spec, lazy=True)


def _build_note(working: WorkingMemoryStore, resolve: ScopeResolver) -> Tool:
    async def memory_note(
        content: str,
        tags: Iterable[str] = (),
        scope_level: str = "run",
    ) -> dict[str, Any]:
        """Append a free-form note to the ``notes`` list in working memory."""
        scope = resolve(scope_level)
        tag_list = list(tags)
        await working.append(scope, "notes", {"content": content, "tags": tag_list})

        return {"ok": True, "scope_level": scope_level, "tags": tag_list}

    spec = _spec(
        "memory_note",
        "Append a free-form note (with optional tags) to working memory.",
        {
            "type": "object",
            "properties": {
                "content": _string_schema("Note body."),
                "tags": {
                    "type": "array",
                    "items": {"type": "string"},
                    "description": "Optional tags to attach to the note.",
                    "default": [],
                },
                "scope_level": _level_schema(),
            },
            "required": ["content"],
        },
    )

    return Tool(memory_note, spec, lazy=True)


__all__ = ["ScopeResolver", "make_memory_tools"]
