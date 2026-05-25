"""Providers package - LLM adapters for Phronesis.

See ``docs/PROVIDERS-DECISIONS.md`` for the design rationale. This
module re-exports the stable public API: vendor factories, the
:class:`LLMProvider` protocol, request/response types, streaming
chunks, token usage, error hierarchy and retry configuration.
"""

from __future__ import annotations

from phronesis.providers.anthropic import anthropic
from phronesis.providers.chunks import (
    Finish,
    LLMChunk,
    TextChunk,
    ToolCallEnd,
    ToolCallStart,
    ToolResult,
)
from phronesis.providers.errors import (
    AuthenticationError,
    BadRequestError,
    ContextWindowExceededError,
    ProviderError,
    RateLimitError,
    ServerError,
    StreamError,
    TransportError,
)
from phronesis.providers.openai import openai
from phronesis.providers.protocol import LLMProvider, ProviderFeature
from phronesis.providers.retry_config import RetryConfig
from phronesis.providers.types import LLMRequest, LLMResponse, Message, Role, ToolCall
from phronesis.providers.usage import TokenUsage

__all__ = [
    "AuthenticationError",
    "BadRequestError",
    "ContextWindowExceededError",
    "Finish",
    "LLMChunk",
    "LLMProvider",
    "LLMRequest",
    "LLMResponse",
    "Message",
    "ProviderError",
    "ProviderFeature",
    "RateLimitError",
    "RetryConfig",
    "Role",
    "ServerError",
    "StreamError",
    "TextChunk",
    "TokenUsage",
    "ToolCall",
    "ToolCallEnd",
    "ToolCallStart",
    "ToolResult",
    "TransportError",
    "anthropic",
    "openai",
]
