#

<div align="center">
  <img src="../../../public/assets/lockup/lockup-horizontal-dark.svg" alt="Phronesis Framework" width="60%" />
</div>

<div align="center">

# Phronesis Framework - `_internal.http`

</div>

<div align="center">
  Async HTTP client on top of <code>httpx</code>: per-phase timeouts, framework-owned error hierarchy, streaming, and sensitive-header redaction.
</div>

<div align="center">
  <a href="../index.md">internal</a> ·
  <a href="../../index.md">docs</a> ·
  <a href="../../../src/phronesis/_internal/http/">source</a> ·
  <a href="../../../tests/_internal/http/">tests</a>
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

A **single, async, observable** HTTP client that all providers (OpenAI, Anthropic, etc.) consume by composition. It isolates the framework from `httpx` details and provides:

- **Framework-owned** request/response types (`HttpRequest`, `HttpResponse`).
- A first-class **error hierarchy**, split between response and transport.
- **Per-phase timeouts** (`connect`, `read`, `write`, `pool`).
- **Streaming** via `async with client.stream(...)`.
- Automatic **redaction** of sensitive headers in logs.
- **Structured logging** of request/response.

<div align="center">

## 🏗️ Architecture

</div>

```
   models.py -----> exceptions.py ----+
        |                              \
        +------------------+            \
                            \            v
   headers.py ------------> client.py
                            ^
   timeouts.py ------------+
```

- `models.py` and `timeouts.py` are pure value objects.
- `exceptions.py` defines the hierarchy.
- `headers.py` handles defaults and redaction.
- `client.py` orchestrates `httpx.AsyncClient` wrapping it with everything above.

<div align="center">

## 📦 Module layout

</div>

| File | Responsibility |
|---|---|
| `models.py` | `HttpRequest` and `HttpResponse` (frozen dataclasses). |
| `timeouts.py` | `HttpTimeouts` with `connect/read/write/pool` and `.to_httpx()`. |
| `exceptions.py` | Hierarchy `HttpError -> {HttpResponseError, HttpTransportError}`. |
| `headers.py` | `build_default_headers()`, `redact_sensitive_headers()`. |
| `client.py` | `HttpClient`, `HttpStreamResponse`, `configure_http_client`. |

<div align="center">

## 🔌 Public API

</div>

```python
from phronesis._internal.http import (
    HttpClient, HttpStreamResponse, configure_http_client,
    HttpRequest, HttpResponse, HttpTimeouts,
    HttpError, HttpResponseError, HttpClientError, HttpServerError,
    HttpTransportError, HttpTimeoutError, HttpConnectionError,
    build_default_headers, redact_sensitive_headers,
)
```

Main methods of `HttpClient`:

| Method | Returns |
|---|---|
| `await client.request(method, url, *, json, content, params, headers, timeouts)` | `HttpResponse` |
| `await client.get/post/put/patch/delete(url, ...)` | `HttpResponse` |
| `client.stream(method, url, ...)` | async context manager -> `HttpStreamResponse` |
| `await client.close()` | - (also supports `async with`) |

<div align="center">

## 📐 Design decisions

</div>

- **Do not re-expose `httpx` to the rest of the framework.** Coupling is confined to this package; switching transports would only touch `client.py`.
- **Errors split by cause.** 4xx -> `HttpClientError`; 5xx -> `HttpServerError`; no response -> `HttpTransportError` (with `HttpTimeoutError` and `HttpConnectionError` as leaves).
- **Per-phase timeouts.** A single global timeout hides very different pathologies; this design makes it clear which phase failed.
- **Streaming as a context manager.** Guarantees `close()` always, even on exceptions; on 4xx/5xx the body is materialized and the appropriate error is raised in `__aenter__`.
- **Header redaction in logs.** `Authorization`, `Cookie`, `Set-Cookie`, `X-Api-Key`, etc. never appear in log records.

<div align="center">

## 📊 Diagrams

</div>

Error hierarchy:

```
                            HttpError
                          /            \
                         /              \
         HttpResponseError            HttpTransportError
         (status_code,                (request, cause)
          response,                       /         \
          request)                       /           \
          /        \              HttpTimeoutError   HttpConnectionError
         /          \
   HttpClientError   HttpServerError
   (4xx)             (5xx)
```

Request/response flow:

```
   Caller         HttpClient                       httpx.AsyncClient
     |                |                                    |
     | request(...)   |                                    |
     |--------------->|                                    |
     |                | log "http request"                 |
     |                |   (headers redacted)               |
     |                |                                    |
     |                | request(...)                       |
     |                |----------------------------------->|
     |                |                                    |
     |                |   TimeoutException --> HttpTimeoutError
     |                |   ConnectError    --> HttpConnectionError
     |                |   2xx/3xx         --> HttpResponse
     |                |   4xx             --> HttpClientError
     |                |   5xx             --> HttpServerError
```

<div align="center">

## 📋 Examples

</div>

```python
import asyncio
from phronesis._internal.http import configure_http_client, HttpTimeouts

async def main() -> None:
    timeouts = HttpTimeouts(connect=5.0, read=30.0, write=10.0, pool=2.0)
    async with configure_http_client(base_url="https://api.example.com", timeouts=timeouts) as http:
        resp = await http.get("/v1/users/42", headers={"Authorization": "Bearer ..."})
        data = resp.json()

asyncio.run(main())
```

```python
from phronesis._internal.http import configure_http_client

async def stream_completion(http_client, payload):
    async with http_client.stream("POST", "/v1/chat", json=payload) as resp:
        async for line in resp.iter_lines():
            print(line)
```

```python
from phronesis._internal.http import HttpClientError, HttpServerError, HttpTransportError

try:
    await http.post("/v1/x", json={...})
except HttpClientError as exc:
    # 4xx: do not retry; the request itself is the problem
    raise
except HttpServerError as exc:
    # 5xx: retryable
    ...
except HttpTransportError as exc:
    # timeout / DNS / network: retryable
    ...
```

<div align="center">

## ⚠️ Pitfalls

</div>

- `HttpClient` keeps a connection pool. **Share one instance** across calls; do not create one per request.
- Forgetting `await client.close()` (or `async with`) leaks connections.
- `client.stream(...)` is **not** awaitable directly: use `async with`.
- In streaming, once the iterator is consumed the body cannot be read again.
- HTTP 4xx/5xx errors arrive as exceptions, not as `HttpResponse`. If the body is needed it lives in `exc.response.content`.

<div align="center">

## 🧪 Testing

</div>

Tests live under `tests/_internal/http/`, backed by `pytest-asyncio` and `httpx` mock transports. They cover:

- Status code mapping to the error hierarchy.
- Timeout and network errors -> `HttpTimeoutError` / `HttpConnectionError`.
- Streaming: iteration, error handling in `__aenter__`, cleanup.
- Sensitive-header redaction in log records.
- `configure_http_client` defaults.

<div align="center">

## 🚦 Quality gates

</div>

```
uv run ruff format src/phronesis/_internal/http tests/_internal/http
uv run ruff check src/phronesis/_internal/http tests/_internal/http
uv run mypy src/phronesis/_internal/http
uv run pytest tests/_internal/http -q
```
