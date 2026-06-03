"""Vector memory: embeddings, similarity search and RAG retrieval.

Public surface:

* :class:`VectorItem` - frozen dataclass for stored items.
* :class:`VectorStore` - structural Protocol for vector backends.
* :class:`EmbeddingProvider` - structural Protocol for embedders.
* :class:`InMemoryVectorStore` - process-local backend.
* :class:`FilesystemJSONVectorStore` - JSONL-per-scope backend.
* :class:`DeterministicEmbeddingProvider` - hash-based reproducible
  embeddings for tests. **Not** a real semantic embedder.
"""

from __future__ import annotations

from phronesis.memory.vector.embeddings import DeterministicEmbeddingProvider
from phronesis.memory.vector.filesystem import FilesystemJSONVectorStore
from phronesis.memory.vector.in_memory import InMemoryVectorStore
from phronesis.memory.vector.protocol import EmbeddingProvider, VectorItem, VectorStore

__all__ = [
    "DeterministicEmbeddingProvider",
    "EmbeddingProvider",
    "FilesystemJSONVectorStore",
    "InMemoryVectorStore",
    "VectorItem",
    "VectorStore",
]
