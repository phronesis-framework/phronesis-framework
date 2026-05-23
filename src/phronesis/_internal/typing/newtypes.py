"""Zero-cost semantic aliases for domain quantities."""

from typing import NewType

Seconds = NewType("Seconds", float)
Milliseconds = NewType("Milliseconds", int)
TokenCount = NewType("TokenCount", int)
PromptTokens = NewType("PromptTokens", int)
CompletionTokens = NewType("CompletionTokens", int)
Cost = NewType("Cost", float)
ByteSize = NewType("ByteSize", int)
