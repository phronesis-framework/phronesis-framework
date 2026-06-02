#

<div align="center">
  <img src="../../../public/assets/lockup/lockup-horizontal-dark.svg" alt="Phronesis Framework" width="60%" />
</div>

<div align="center">

# Phronesis Framework - `_internal.concurrency`

</div>

<div align="center">
  Concurrency utilities: <code>run_sync</code> for thread offloading and <code>gather_all</code> with policies (<code>FailFast</code>, <code>BestEffort</code>) and partial failures.
</div>

<div align="center">
  <a href="../index.md">internal</a> ·
  <a href="../../index.md">docs</a> ·
  <a href="../../../src/phronesis/_internal/concurrency/">source</a> ·
  <a href="../../../tests/_internal/concurrency/">tests</a>
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

A thin layer on top of `asyncio` covering the two recurring patterns in the framework:

- **Offload blocking code to a thread** from async code (`run_sync`).
- **Run N awaitables concurrently** reconciling errors with an explicit policy (`gather_all` + `GatherPolicy`).

Both operations emit structured logs under `phronesis.concurrency`.

<div align="center">

## 🏗️ Architecture

</div>

```
   exceptions.py ----> policies.py ----+
        |                                \
        |                                 v
        +----------------------------> gather.py

   executor.py    (independent)
```

- `executor.py` is standalone; it wraps `asyncio.to_thread`.
- `policies.py` defines `GatherPolicy` (Strategy) and two implementations.
- `gather.py` applies the policy on top of `asyncio.gather`.
- `exceptions.py` defines `ConcurrencyError` and `PartialFailureError`.

<div align="center">

## 📦 Module layout

</div>

| File | Responsibility |
|---|---|
| `executor.py` | `run_sync(fn, *args, **kwargs)` - wrapper around `asyncio.to_thread` with logging. |
| `policies.py` | `GatherPolicy` (ABC), `FailFastPolicy`, `BestEffortPolicy`. |
| `gather.py` | `gather_all(*awaitables, policy=...)`. |
| `exceptions.py` | `ConcurrencyError`, `PartialFailureError` (with `results` and `exceptions`). |

<div align="center">

## 🔌 Public API

</div>

```python
from phronesis._internal.concurrency import (
    run_sync,
    gather_all,
    GatherPolicy, FailFastPolicy, BestEffortPolicy,
    ConcurrencyError, PartialFailureError,
)
```

<div align="center">

## 📐 Design decisions

</div>

- **Explicit policy.** `gather_all` rejects an implicit "what to do on error": either `FailFastPolicy` (default) or `BestEffortPolicy`. Changing the semantics requires a conscious choice.
- **`PartialFailureError` preserves order.** `results[i]` and `exceptions[i]` correspond to task `i`: one of the two is `None`. This enables retrying only what failed.
- **`run_sync` does not accept a custom executor.** Keep it simple; uses asyncio's default executor.
- **Built-in logging.** All operations emit `start` / `done` with duration. Any consumer gets observability "for free".
- **No retry here.** Retrying is the responsibility of the `@retry` decorator; this package only expresses "run concurrently with this policy".

<div align="center">

## 📊 Diagrams

</div>

Policy hierarchy:

```
                +---------------------------+
                |       GatherPolicy        |  <<abstract>>
                +---------------------------+
                | + return_exceptions: bool |
                | + reconcile(results) list |
                +-------+--------------+----+
                        ^              ^
                        |              |
              +---------+----+    +----+-------------+
              | FailFast     |    | BestEffort       |
              | Policy       |    | Policy           |
              | (False)      |    | (True)           |
              +--------------+    +------------------+

                +---------------------+
                |  ConcurrencyError   |
                +----------+----------+
                           ^
                           |
                +----------+-------------+
                | PartialFailureError    |
                |  + results: list       |
                |  + exceptions: list    |
                |  + failed_count        |
                |  + successful_count    |
                +------------------------+
```

`gather_all` with `BestEffortPolicy`:

```
   Caller       gather_all          Policy             asyncio
     |              |                  |                  |
     | gather_all(a,b,c,               |                  |
     |   policy=BestEffort())          |                  |
     |------------->|                  |                  |
     |              | gather(a,b,c,                       |
     |              |   return_exceptions=True)           |
     |              |------------------------------------>|
     |              |                  | [v_a, exc_b, v_c]|
     |              |<------------------------------------|
     |              | reconcile([v_a, exc_b, v_c])        |
     |              |----------------->|                  |
     |              |                  |                  |
     |   raise PartialFailureError(                       |
     |     results=[v_a, None, v_c],                      |
     |     exceptions=[None, exc_b, None])                |
     |<--------------------------------                   |
```

<div align="center">

## 📋 Examples

</div>

```python
from phronesis._internal.concurrency import run_sync

def parse_pdf(path: str) -> str:
    # third-party CPU/IO-blocking function
    ...

text = await run_sync(parse_pdf, "/tmp/doc.pdf")
```

```python
from phronesis._internal.concurrency import gather_all, FailFastPolicy

# fail-fast (default): the first exception cancels the rest
results = await gather_all(
    call_provider_a(),
    call_provider_b(),
    call_provider_c(),
)
```

```python
from phronesis._internal.concurrency import gather_all, BestEffortPolicy, PartialFailureError

try:
    results = await gather_all(
        embed(chunk_1),
        embed(chunk_2),
        embed(chunk_3),
        policy=BestEffortPolicy(),
    )
except PartialFailureError as exc:
    for i, err in enumerate(exc.exceptions):
        if err is not None:
            log.warning("chunk %d failed", i, extra={"error": str(err)})
    # retry only what failed
    to_retry = [i for i, e in enumerate(exc.exceptions) if e is not None]
```

<div align="center">

## ⚠️ Pitfalls

</div>

- `FailFastPolicy` cancels pending tasks, but does **not** guarantee they stop immediately: a task that ignores cancellation can keep running.
- `BestEffortPolicy` always **waits for all**: use with care if tasks can hang (combine with timeouts).
- `run_sync` is not meant for pure CPU-bound work: the GIL limits real parallelism. For heavy CPU work consider an external `ProcessPoolExecutor`.
- `PartialFailureError.results` and `exceptions` are **parallel lists**: never filter one without the other.
- Passing already-awaited coroutines to `gather_all` raises `RuntimeError` from `asyncio`.

<div align="center">

## 🧪 Testing

</div>

Tests live under `tests/_internal/concurrency/`:

- `run_sync`: success, exception propagation, logging emitted.
- `FailFastPolicy`: first exception propagates; remaining tasks cancelled.
- `BestEffortPolicy`: result order preserved; `PartialFailureError` with correct counts; no-failure case returns a flat list.
- `gather_all` without a policy uses `FailFastPolicy` by default.

<div align="center">

## 🚦 Quality gates

</div>

```
uv run ruff format src/phronesis/_internal/concurrency tests/_internal/concurrency
uv run ruff check src/phronesis/_internal/concurrency tests/_internal/concurrency
uv run mypy src/phronesis/_internal/concurrency
uv run pytest tests/_internal/concurrency -q
```
