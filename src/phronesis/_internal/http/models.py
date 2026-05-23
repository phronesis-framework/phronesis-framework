"""Framework-owned HTTP request/response value objects."""

from __future__ import annotations

import json as _json
from collections.abc import Mapping
from dataclasses import dataclass
from typing import Any


@dataclass(frozen=True, slots=True)
class HttpRequest:
    """Snapshot of the request sent to the server."""

    method: str
    url: str
    headers: Mapping[str, str]
    content: bytes | None


@dataclass(frozen=True, slots=True)
class HttpResponse:
    """Snapshot of the response received from the server."""

    status_code: int
    headers: Mapping[str, str]
    content: bytes
    text: str
    duration_ms: float

    def json(self) -> Any:
        """Decode :attr:`content` as JSON."""
        return _json.loads(self.content)
