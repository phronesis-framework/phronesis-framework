"""Error hierarchy for the :mod:`phronesis.replay` package.

:class:`ReplayError` is the cross-cutting base every replay-related
failure inherits from. :class:`CassetteFormatError` narrows it to
failures decoding a cassette file; :class:`CassetteExhaustedError`
narrows it to attempts to read past the last recorded entry.
"""

from __future__ import annotations

from phronesis.errors import PhronesisError


class ReplayError(PhronesisError):
    """Base class for every failure originating in :mod:`phronesis.replay`."""


class CassetteFormatError(ReplayError):
    """Raised when a cassette file cannot be parsed."""


class CassetteExhaustedError(ReplayError):
    """Raised when :class:`ReplayProvider` is asked for more responses than recorded."""
