"""Record and replay provider responses to disk.

Public API:

- :class:`RecordingProvider` wraps a real provider and appends each
  completion to a JSONL cassette file.
- :class:`ReplayProvider` reads a cassette and serves the recorded
  responses in order without any network access.
- :func:`read_cassette` / :func:`write_cassette` / :func:`append_cassette`
  are the underlying cassette helpers, exposed for callers that need
  to build or inspect cassettes directly.

Streaming is not supported in the MVP; cassettes only contain
non-streaming :class:`LLMResponse` entries.
"""

from __future__ import annotations

from phronesis.replay.cassette import (
    append_cassette as append_cassette,
)
from phronesis.replay.cassette import (
    decode_response as decode_response,
)
from phronesis.replay.cassette import (
    encode_response as encode_response,
)
from phronesis.replay.cassette import (
    read_cassette as read_cassette,
)
from phronesis.replay.cassette import (
    write_cassette as write_cassette,
)
from phronesis.replay.errors import (
    CassetteExhaustedError as CassetteExhaustedError,
)
from phronesis.replay.errors import (
    CassetteFormatError as CassetteFormatError,
)
from phronesis.replay.errors import (
    ReplayError as ReplayError,
)
from phronesis.replay.recording import RecordingProvider as RecordingProvider
from phronesis.replay.replay import ReplayProvider as ReplayProvider

__all__ = [
    "CassetteExhaustedError",
    "CassetteFormatError",
    "RecordingProvider",
    "ReplayError",
    "ReplayProvider",
    "append_cassette",
    "decode_response",
    "encode_response",
    "read_cassette",
    "write_cassette",
]
