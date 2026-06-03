"""Key-value memory: TTL-aware, atomic-op-capable storage.

Public surface:

* :class:`KeyValueStore` - structural Protocol that backends satisfy.
* :class:`InMemoryKeyValueStore` - process-local backend with lazy TTL.
* :class:`FilesystemJSONKeyValueStore` - JSON-per-scope backend with
  atomic writes via ``tempfile + os.replace``.
"""

from __future__ import annotations

from phronesis.memory.kv.filesystem import FilesystemJSONKeyValueStore
from phronesis.memory.kv.in_memory import InMemoryKeyValueStore
from phronesis.memory.kv.protocol import KeyValueStore

__all__ = [
    "FilesystemJSONKeyValueStore",
    "InMemoryKeyValueStore",
    "KeyValueStore",
]
