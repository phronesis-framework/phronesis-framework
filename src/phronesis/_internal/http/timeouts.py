"""Per-phase HTTP timeout configuration."""

from __future__ import annotations

from dataclasses import dataclass

import httpx


@dataclass(frozen=True, slots=True)
class HttpTimeouts:
    """Separate timeouts for connect, read, write, and pool acquisition.

    Values are in seconds. ``None`` disables that phase's timeout.
    """

    connect: float | None = 10.0
    read: float | None = 60.0
    write: float | None = 10.0
    pool: float | None = 5.0

    def to_httpx(self) -> httpx.Timeout:
        """Return the equivalent :class:`httpx.Timeout`."""
        return httpx.Timeout(
            connect=self.connect,
            read=self.read,
            write=self.write,
            pool=self.pool,
        )
