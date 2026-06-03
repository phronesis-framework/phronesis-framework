"""Long-lived memory stores for agents.

The package provides four orthogonal memory variants:

* :class:`WorkingMemoryStore` - short-lived scratchpad per run/scope.
* :class:`KeyValueStore` - TTL-aware KV store with atomic ops
  (compare-and-swap, append, increment) for blackboard patterns.
* :class:`VectorStore` - embedding-based similarity search for RAG.
* :class:`EpisodicStore` - append-only event log used by checkpoints.

Each store ships with two backends: ``InMemory*`` and
``FilesystemJSON*``. The :class:`Checkpointer` builds on top of
working + episodic to provide pause/resume semantics.

Three integration points hook memory into the framework:

* :class:`MemoryAwareContextBuilder` (RAG into prompts).
* :func:`make_memory_tools` (model-controlled remember/recall).
* :class:`MemoryPersistenceHook` (lifecycle persistence).
"""

from __future__ import annotations

from phronesis.memory.checkpoint import (
    CHECKPOINT_RESTORED_TYPE,
    CHECKPOINT_TYPE,
    Checkpoint,
    Checkpointer,
)
from phronesis.memory.context_builder import (
    InjectionPosition,
    MemoryAwareContextBuilder,
)
from phronesis.memory.episodic import (
    Episode,
    EpisodicStore,
    FilesystemJSONEpisodicStore,
    InMemoryEpisodicStore,
)
from phronesis.memory.errors import (
    CheckpointNotFoundError,
    MemoryBackendError,
    MemoryError,
    MemoryKeyError,
    MemoryScopeError,
)
from phronesis.memory.hooks import MemoryPersistenceHook, ScopeFromResult
from phronesis.memory.kv import (
    FilesystemJSONKeyValueStore,
    InMemoryKeyValueStore,
    KeyValueStore,
)
from phronesis.memory.scope import MemoryLevel, MemoryScope
from phronesis.memory.tools import ScopeResolver, make_memory_tools
from phronesis.memory.vector import (
    DeterministicEmbeddingProvider,
    EmbeddingProvider,
    FilesystemJSONVectorStore,
    InMemoryVectorStore,
    VectorItem,
    VectorStore,
)
from phronesis.memory.working import InMemoryWorkingStore, WorkingMemoryStore

__all__ = [
    "CHECKPOINT_RESTORED_TYPE",
    "CHECKPOINT_TYPE",
    "Checkpoint",
    "CheckpointNotFoundError",
    "Checkpointer",
    "DeterministicEmbeddingProvider",
    "EmbeddingProvider",
    "Episode",
    "EpisodicStore",
    "FilesystemJSONEpisodicStore",
    "FilesystemJSONKeyValueStore",
    "FilesystemJSONVectorStore",
    "InMemoryEpisodicStore",
    "InMemoryKeyValueStore",
    "InMemoryVectorStore",
    "InMemoryWorkingStore",
    "InjectionPosition",
    "KeyValueStore",
    "MemoryAwareContextBuilder",
    "MemoryBackendError",
    "MemoryError",
    "MemoryKeyError",
    "MemoryLevel",
    "MemoryPersistenceHook",
    "MemoryScope",
    "MemoryScopeError",
    "ScopeFromResult",
    "ScopeResolver",
    "VectorItem",
    "VectorStore",
    "WorkingMemoryStore",
    "make_memory_tools",
]
