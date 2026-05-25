#

<div align="center">
  <img src="../../../public/assets/lockup/lockup-horizontal-dark.svg" alt="Phronesis Framework" width="60%" />
</div>

<div align="center">

# Phronesis Framework - `providers.openai`

</div>

<div align="center">
  OpenAI adapter for the <code>providers</code> module. Targets the Chat Completions API at <code>/v1/chat/completions</code>, in both synchronous and streaming modes, without any vendor SDK.
</div>

<div align="center">
  <a href="../index.md">providers</a> ·
  <a href="../../index.md">docs</a> ·
  <a href="../../../src/phronesis/providers/openai/">source</a> ·
  <a href="../../../tests/providers/openai/">tests</a>
</div>

<div align="center">

[![Status](https://img.shields.io/badge/status-stable-green)]()
[![Coverage](https://img.shields.io/badge/coverage-100%25-brightgreen)]()
[![Python](https://img.shields.io/badge/python-3.11+-blue?logo=python&logoColor=white)]()

</div>

---

<div align="center">

## 🎯 Purpose

</div>

Translate the framework's `LLMRequest` / `LLMResponse` types into OpenAI Chat Completions API calls. Speak SSE for streaming, map HTTP errors to the shared `ProviderError` hierarchy, and expose the vendor-specific feature set via `ProviderFeature`.

Public entry point is the [`openai`](../../../src/phronesis/providers/openai/factory.py) factory function; the `OpenAIProvider` class is framework-internal.

<div align="center">

## 🏗️ Wire shape

</div>

| Concern | Value |
|---|---|
| Endpoint | `POST /v1/chat/completions` |
| Auth header | `Authorization: Bearer $OPENAI_API_KEY` |
| Streaming | body `stream: true`; SSE with `data:` lines terminated by `data: [DONE]` |
| Streaming usage | body `stream_options: {include_usage: true}` forced by the adapter |
| Required body | `model`, `messages` (`max_tokens` optional; `None` lets the model decide) |
| System prompt | prepended as a regular `{"role": "system"}` message (extracted from `Role.SYSTEM` or `LLMRequest.system`) |
| Tools | top-level `tools: [{type: "function", function: {name, parameters, description?}}]` |
| Tool results | `{"role": "tool", "tool_call_id": "...", "content": "..."}` messages |

<div align="center">

## 🔌 Feature support

</div>

| Feature | Supported | Notes |
|---|:-:|---|
| `STRUCTURED_OUTPUT` | yes | Caller supplies `response_format` via `metadata`. |
| `REASONING_EFFORT` | yes | Caller supplies `reasoning_effort` via `metadata`. |
| `PREDICTED_OUTPUTS` | yes | Caller supplies `prediction` via `metadata`. |
| `PROMPT_CACHING` | yes | Reported in `usage.cached_tokens` (read from `prompt_tokens_details.cached_tokens`). |
| `VISION` | yes | Image parts travel as content blocks (caller-supplied). |
| `DOCUMENTS` | no | Not native to the Chat Completions API. |
| `EXTENDED_THINKING` | no | Anthropic-only knob. |

<div align="center">

## 📊 Streaming event mapping

</div>

```mermaid
flowchart LR
    Sse[SSE data frame] --> Done{is [DONE]?}
    Done -- yes --> Stop[stop iteration]
    Done -- no --> Choices[parse choices/usage]
    Choices --> Delta{delta?}
    Delta -- content --> Text[TextChunk]
    Delta -- tool_calls --> Buffer[buffer per index]
    Choices --> Finish{finish_reason?}
    Finish -- yes --> Flush[ToolCallEnd for each buffered tool]
    Flush --> Done2[Finish chunk + usage]
```

Tool calls arrive across many delta frames keyed by `index`; each fragment contributes a partial JSON string to the `arguments` buffer for that index. The streaming layer emits `ToolCallStart` the first time an `index` is seen and flushes `ToolCallEnd` (with parsed arguments) when the stream completes. Invalid JSON raises `StreamError`.

`stream_options.include_usage = true` is forced by the adapter so the final `usage` block always arrives before `[DONE]`.

<div align="center">

## 📐 Error mapping

</div>

| HTTP status | Maps to |
|---|---|
| 401, 403 | `AuthenticationError` |
| 429 | `RateLimitError(retry_after_seconds=...)` |
| 400 with `code` in `{context_length_exceeded, string_above_max_length}` | `ContextWindowExceededError` |
| 400 | `BadRequestError` |
| 5xx | `ServerError` |
| other | `BadRequestError` |

`RateLimitError` parses the `retry-after` response header when present (decimal seconds).

<div align="center">

## 📋 Example

</div>

```python
from phronesis.providers.openai import openai
from phronesis.providers.types import LLMRequest, Message, Role

provider = openai(
    "gpt-4o",
    api_key="sk-...",         # or set OPENAI_API_KEY
    temperature=0.2,
)

response = await provider.complete(
    LLMRequest(
        model="",
        messages=(
            Message(role=Role.SYSTEM, content="Be concise."),
            Message(role=Role.USER, content="Three uses for vinegar."),
        ),
    )
)

print(response.text)
print(response.usage.cached_tokens)
```

<div align="center">

## ⚠️ Pitfalls

</div>

- **`max_tokens` is optional.** Unlike Anthropic, OpenAI lets the model decide when `max_tokens` is omitted. The factory does not set a default.
- **Streaming is not retried.** `complete` retries on `TransportError`, `RateLimitError`, `ServerError` via `RetryConfig`; `stream` does not.
- **Tool arguments arrive as JSON strings.** The framework parses them at `ToolCallEnd`; invalid JSON ends the iterator with `StreamError`.
- **System prompts are prepended as messages**, not extracted into a separate top-level field. Multiple `Role.SYSTEM` messages and `LLMRequest.system` are concatenated in order.
- **`stream_options.include_usage` is forced to `true`** so callers receive a final usage report; passing a different value in `metadata` will be overridden.

<div align="center">

## 🧪 Testing

</div>

| Test file | What it covers |
|---|---|
| `test_errors.py` | Status / envelope -> `ProviderError`. |
| `test_messages.py` | `Message` <-> OpenAI encoding, tool roles, assistant tool_calls. |
| `test_tools.py` | `ToolSpec` -> OpenAI function envelope. |
| `test_provider.py` | Header / body shape, complete path, retries, system composition, usage parsing. |
| `test_streaming.py` | SSE parser, text deltas, tool buffering, mixed content, `[DONE]` sentinel. |
| `test_factory.py` | Env var fallback, explicit key precedence, default client. |
