#

<div align="center">
  <img src="../../../public/assets/lockup/lockup-horizontal-dark.svg" alt="Phronesis Framework" width="60%" />
</div>

<div align="center">

# Phronesis Framework - `_internal.retry`

</div>

<div align="center">
  <code>@retry</code> decorator for async callables, configurable backoffs (fixed and exponential with jitter), and full attempt history.
</div>

<div align="center">
  <a href="../index.md">internal</a> ·
  <a href="../../index.md">docs</a> ·
  <a href="../../../src/phronesis/_internal/retry/">source</a> ·
  <a href="../../../tests/_internal/retry/">tests</a>
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

External calls (LLMs, vector stores, APIs) are **transient by nature**. This module provides an opinionated but configurable `@retry` decorator that:

- Retries only the declared exceptions (`on=(...)`).
- Allows an additional filter (`should_retry(exc) -> bool`).
- Picks the delay with priority **hook -> `retry_after_seconds` -> backoff**.
- Is **transport-agnostic**: it knows nothing about HTTP. The coupling with `_internal.http` is by convention (a `retry_after_seconds` attribute on the exception).
- Raises `RetryExhaustedError` with the **full history** when attempts are exhausted.

<div align="center">

## 🏗️ Architecture

</div>

```
   attempt.py ----+----> exceptions.py
                  |              \
                  |               \
                  +----> decorator.py
                                ^
   backoff.py -------------------+
```

- `attempt.py` defines the per-attempt accounting.
- `backoff.py` defines the `BackoffStrategy` protocol and two implementations.
- `exceptions.py` defines `RetryError` and `RetryExhaustedError`.
- `decorator.py` orchestrates the retry loop.

<div align="center">

## 📦 Module layout

</div>

| File | Responsibility |
|---|---|
| `attempt.py` | `AttemptInfo` - number, exception, duration, next delay. |
| `backoff.py` | `BackoffStrategy` (Protocol), `FixedBackoff`, `ExponentialBackoff` (optional full-jitter). |
| `exceptions.py` | `RetryError`, `RetryExhaustedError` (with history). |
| `decorator.py` | `@retry(...)` and `_calculate_delay` with priority. |

<div align="center">

## 🔌 Public API

</div>

```python
from phronesis._internal.retry import (
    retry,
    BackoffStrategy, FixedBackoff, ExponentialBackoff,
    AttemptInfo,
    RetryError, RetryExhaustedError,
)
```

Decorator signature:

```python
def retry(
    *,
    on: tuple[type[BaseException], ...],
    max_attempts: int = 3,
    should_retry: Callable[[Exception], bool] | None = None,
    backoff: BackoffStrategy | None = None,        # default: ExponentialBackoff()
    honor_retry_after: bool = True,
    delay_hook: Callable[[Exception], float | None] | None = None,
    log_level: int = logging.INFO,
) -> Callable[[Callable[P, Awaitable[T]]], Callable[P, Awaitable[T]]]: ...
```

<div align="center">

## 📐 Design decisions

</div>

- **Async only.** The framework is async-first; no sync version is maintained.
- **`on=(...)` mandatory.** No "retry everything": the caller explicitly declares which exceptions are transient.
- **Additional `should_retry`.** Allows a fine-grained filter without losing the typing of `on=`.
- **Clear delay priority.** `delay_hook` > `retry_after_seconds` (if `honor_retry_after`) > `backoff`. Documented and tested.
- **`retry_after_seconds` by convention.** The decorator does not import from HTTP; any exception that exposes that attribute (e.g. a mapped 429) is honored.
- **Full history in the final error.** `RetryExhaustedError.attempt_history` enables post-mortem observability without extra instrumentation.
- **`ExponentialBackoff` with full-jitter by default.** Avoids thundering herd: `delay * random.uniform(0.5, 1.5)`.

<div align="center">

## 📊 Diagrams

</div>

Retry state machine:

```
            +---------+
            |         |
            v         |  await sleep(delay)
       +---------+    |
   --> | Attempt |----+
       +---------+
        |   |   |
   ok   |   |   | raises
        v   |   |
    Success |   v
        |   | (exc not in on or should_retry == False) --> Propagate
        |   |
        |   v
        | (attempt >= max_attempts) --> raise RetryExhaustedError
        |
        v
       end
```

Delay selection:

```
   exception
       |
       v
   delay_hook is not None and returns non-None ?
       |                                |
      yes                               no
       |                                |
       v                                v
   use hook value           honor_retry_after and exc.retry_after_seconds ?
                                |                                  |
                               yes                                 no
                                |                                  |
                                v                                  v
                           use retry_after                backoff.get_delay(attempt)
```

<div align="center">

## 📋 Examples

</div>

```python
from phronesis._internal.retry import retry, ExponentialBackoff
from phronesis._internal.http import HttpServerError, HttpTransportError

@retry(
    on=(HttpServerError, HttpTransportError),
    max_attempts=5,
    backoff=ExponentialBackoff(initial=0.5, max_delay=8.0, jitter=True),
)
async def call_provider(client, payload):
    return await client.post("/v1/chat", json=payload)
```

```python
from phronesis._internal.retry import retry, FixedBackoff

@retry(
    on=(ConnectionError,),
    max_attempts=3,
    backoff=FixedBackoff(delay=1.0),
    should_retry=lambda exc: "temporary" in str(exc).lower(),
)
async def fetch(): ...
```

```python
from phronesis._internal.retry import RetryExhaustedError

try:
    await call_provider(client, payload)
except RetryExhaustedError as exc:
    log.error(
        "all retries failed",
        extra={
            "attempts": exc.attempts,
            "total_duration_ms": exc.total_duration_ms,
            "last_error": str(exc.last_exception),
        },
    )
```

<div align="center">

## ⚠️ Pitfalls

</div>

- `on=` must contain the **classes** of the transient exceptions. Any exception outside that tuple is **propagated without retry**.
- `should_retry=False` aborts the retry even if the exception is in `on=`.
- `ExponentialBackoff` with `jitter=False` under heavy load causes a thundering herd: leave `jitter=True` unless you have a clear reason.
- The history (`attempt_history`) can be large: do not log the whole thing in production.
- The decorator is **async only**; applying it to a sync function is a type error.

<div align="center">

## 🧪 Testing

</div>

Tests live under `tests/_internal/retry/`:

- Exact attempt count up to success and up to `RetryExhaustedError`.
- Delay priority: hook > `retry_after_seconds` > backoff.
- Exceptions outside `on=` propagate on the first attempt.
- `should_retry=False` does not retry.
- `FixedBackoff` and `ExponentialBackoff` (with and without jitter) - delay range validated.
- Logging emitted on each retry and on exhaustion.

<div align="center">

## 🚦 Quality gates

</div>

```
uv run ruff format src/phronesis/_internal/retry tests/_internal/retry
uv run ruff check src/phronesis/_internal/retry tests/_internal/retry
uv run mypy src/phronesis/_internal/retry
uv run pytest tests/_internal/retry -q
```
