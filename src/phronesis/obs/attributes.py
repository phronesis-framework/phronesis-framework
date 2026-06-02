"""Closed catalog of standard span attribute names.

All Phronesis components emit attributes with the names defined here so
dashboards and queries remain consistent across tools, providers,
agents, runtime and pipelines.

The variability of each operation (which concrete tool, which provider,
which agent) goes into these attributes rather than into the span name,
keeping cardinality controlled and filtering predictable.

Naming follows the OpenTelemetry semantic conventions: lower case,
dot-separated, no underscores at the segment boundaries.

Catalog sections:

- **Identifiers** — IDs and names of framework entities.
- **Provider** — LLM provider metadata.
- **Operation** — outcome and timing of a single operation.
- **Tokens** — token counts and cost reported by providers.
- **Streaming** — metadata for streaming responses.
"""

from __future__ import annotations

from typing import Final

# Identifiers ---------------------------------------------------------

TOOL_ID: Final[str] = "tool.id"
TOOL_TID: Final[str] = "tool.tid"
TOOL_NAME: Final[str] = "tool.name"

AGENT_ID: Final[str] = "agent.id"
AGENT_NAME: Final[str] = "agent.name"

PIPELINE_ID: Final[str] = "pipeline.id"
PIPELINE_NAME: Final[str] = "pipeline.name"

RUN_ID: Final[str] = "run.id"
SESSION_ID: Final[str] = "session.id"
TOOL_CALL_ID: Final[str] = "tool_call.id"
MESSAGE_ID: Final[str] = "message.id"

# Provider ------------------------------------------------------------

PROVIDER_NAME: Final[str] = "provider.name"
PROVIDER_MODEL: Final[str] = "provider.model"

# Operation -----------------------------------------------------------

OPERATION_DURATION_MS: Final[str] = "operation.duration_ms"
OPERATION_SUCCESS: Final[str] = "operation.success"

ERROR_TYPE: Final[str] = "error.type"
ERROR_MESSAGE: Final[str] = "error.message"

# Tokens --------------------------------------------------------------

TOKENS_INPUT: Final[str] = "tokens.input"
TOKENS_OUTPUT: Final[str] = "tokens.output"
TOKENS_TOTAL: Final[str] = "tokens.total"
COST_USD: Final[str] = "cost.usd"

# Streaming -----------------------------------------------------------

STREAM_CHUNKS_COUNT: Final[str] = "stream.chunks_count"
STREAM_FIRST_CHUNK_MS: Final[str] = "stream.first_chunk_ms"

# Context -------------------------------------------------------------

CONTEXT_BUILDER: Final[str] = "context.builder"
CONTEXT_HISTORY_SIZE: Final[str] = "context.history_size"
CONTEXT_COMPACTED: Final[str] = "context.compacted"
