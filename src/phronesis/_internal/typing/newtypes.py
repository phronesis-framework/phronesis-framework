"""Semantic :func:`typing.NewType` aliases for domain quantities.

Each :func:`typing.NewType` is zero-cost at runtime (an identity function)
but distinct to the type checker. The intent is to prevent accidental
mixing of values that share a primitive representation yet mean different
things — for example, adding seconds to milliseconds, or treating a token
count as a dollar amount.

Use them at every boundary that exchanges these quantities (signatures of
providers, budgets, schedulers, traces). The type checker will flag
mismatches; the runtime will not.
"""

from typing import NewType

Seconds = NewType("Seconds", float)
"""A duration in seconds."""

Milliseconds = NewType("Milliseconds", int)
"""A duration in milliseconds (integer)."""

TokenCount = NewType("TokenCount", int)
"""A total count of tokens (either direction)."""

PromptTokens = NewType("PromptTokens", int)
"""Tokens consumed by the prompt portion of a request."""

CompletionTokens = NewType("CompletionTokens", int)
"""Tokens emitted as completion by a model."""

Cost = NewType("Cost", float)
"""A monetary amount cost agnostic."""

ByteSize = NewType("ByteSize", int)
"""A size measured in bytes."""
