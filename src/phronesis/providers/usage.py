"""Token usage reporting.

See ``docs/PROVIDERS-DECISIONS.md`` (D-10): providers expose raw token
counts as reported by their API. Cost calculation is out of scope.
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
        cache_read_tokens: Tokens served from prompt cache (Anthropic) or
            cached input (OpenAI).
        cache_creation_tokens: Tokens written to the prompt cache.
    """

    input_tokens: int | None = None
    output_tokens: int | None = None
    cache_read_tokens: int | None = None
    cache_creation_tokens: int | None = None
