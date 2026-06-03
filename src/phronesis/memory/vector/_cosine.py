"""Pure-Python cosine similarity shared by the in-memory and FS backends."""

from __future__ import annotations

import math
from collections.abc import Sequence

_ZERO_NORM_THRESHOLD = 1e-12


def cosine_similarity(a: Sequence[float], b: Sequence[float]) -> float:
    """Return the cosine similarity of ``a`` and ``b`` in ``[-1.0, 1.0]``.

    Returns ``0.0`` when either vector has zero magnitude or when the
    two vectors have mismatched length (callers are responsible for
    keeping dimensions consistent, but a numerically safe default is
    preferable to raising during a search).
    """
    if len(a) != len(b):
        return 0.0

    dot = 0.0
    norm_a = 0.0
    norm_b = 0.0

    for x, y in zip(a, b, strict=True):
        dot += x * y
        norm_a += x * x
        norm_b += y * y

    if norm_a < _ZERO_NORM_THRESHOLD or norm_b < _ZERO_NORM_THRESHOLD:
        return 0.0

    return dot / (math.sqrt(norm_a) * math.sqrt(norm_b))
