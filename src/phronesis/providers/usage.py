"""Token usage reporting.

Providers expose raw token counts as reported by their API. Cost
calculation is out of scope and left to callers, who know their
pricing tier. Fields that the underlying API does not report are
left as ``None`` so consumers can distinguish "absent" from "zero".
"""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True, slots=True)
class TokenUsage:
    """Token counts reported by a provider for a single completion.

    All fields are ``None`` when the provider does not expose the metric.

    Attributes:
        input_tokens: Tokens in the prompt.
        output_tokens: Tokens produced by the model.
        cache_read_tokens: Tokens served from a prompt cache (when
            the provider supports prompt caching).
        cache_creation_tokens: Tokens written to the prompt cache on
            this request.
    """

    input_tokens: int | None = None
    output_tokens: int | None = None
    cache_read_tokens: int | None = None
    cache_creation_tokens: int | None = None
