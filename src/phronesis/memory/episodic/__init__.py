"""Episodic memory: append-only audit trail of significant events.

Public surface:

* :class:`Episode` - frozen dataclass for recorded events.
* :class:`EpisodicStore` - structural Protocol for backends.
* :class:`InMemoryEpisodicStore` - process-local backend.
* :class:`FilesystemJSONEpisodicStore` - JSONL append-only backend.
"""

from __future__ import annotations

from phronesis.memory.episodic.filesystem import FilesystemJSONEpisodicStore
from phronesis.memory.episodic.in_memory import InMemoryEpisodicStore
from phronesis.memory.episodic.protocol import Episode, EpisodicStore

__all__ = [
    "Episode",
    "EpisodicStore",
    "FilesystemJSONEpisodicStore",
    "InMemoryEpisodicStore",
]
