#

<div align="center">
  <img src="../../../public/assets/lockup/lockup-horizontal-dark.svg" alt="Phronesis Framework" width="60%" />
</div>

<div align="center">

# Phronesis Framework — `_internal.logging`

</div>

<div align="center">
  Structured (JSON) and human-readable logging on top of <code>stdlib logging</code>: formatters, context adapter, factory, and idempotent configuration.
</div>

<div align="center">
  <a href="../index.md">internal</a> ·
  <a href="../../index.md">docs</a> ·
  <a href="../../../src/phronesis/_internal/logging/">source</a> ·
  <a href="../../../tests/_internal/logging/">tests</a>
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

The whole framework emits logs under the `phronesis.*` namespace. This package provides:

- A **single managed handler** installed idempotently on the `phronesis` root logger.
- Two first-class formatters: `StructuredFormatter` (JSON, for production/ingest) and `HumanReadableFormatter` (for development).
- A `ContextLoggerAdapter` that injects fixed context into every record (request_id, agent_id, …) without passing it manually.
- A minimal factory (`get_logger`, `get_logger_with_context`) that avoids exposing `logging.getLogger` directly to the rest of the code.

The user's global `logging` configuration is never touched: only the `phronesis` namespace.

<div align="center">

## 🏗️ Architecture

</div>

```
   constants.py ----+------> config.py
                    |          ^
   formatters.py ---+----------+
                    |
                    +------> factory.py
                                ^
   adapter.py --------------+---+
```

- `constants.py` defines the root namespace and default level.
- `formatters.py` defines the two supported representations.
- `config.py` orchestrates idempotent setup on the `phronesis` root logger.
- `factory.py` exposes `get_logger` and `get_logger_with_context`.
- `adapter.py` defines `ContextLoggerAdapter`.

<div align="center">

## 📦 Module layout

</div>

| File | Responsibility |
|---|---|
| `constants.py` | `PHRONESIS_LOGGER_PREFIX = "phronesis"`, `DEFAULT_LEVEL = WARNING`. |
| `formatters.py` | `StructuredFormatter` (JSON line) and `HumanReadableFormatter`. |
| `config.py` | `configure_logging(level, structured, stream)` — installs a managed handler, replaces the previous one. |
| `factory.py` | `get_logger(name)`, `get_logger_with_context(name, **context)`. |
| `adapter.py` | `ContextLoggerAdapter` — merge of fixed context + call-site `extra`. |

<div align="center">

## 🔌 Public API

</div>

```python
from phronesis._internal.logging import (
    configure_logging,
    get_logger,
    get_logger_with_context,
    ContextLoggerAdapter,
    StructuredFormatter,
    HumanReadableFormatter,
    PHRONESIS_LOGGER_PREFIX,
    DEFAULT_LEVEL,
)
```

<div align="center">

## 📐 Design decisions

</div>

- **Only the `phronesis` namespace.** The user's `root` logger is never touched; the framework coexists with any pre-existing configuration.
- **Marked and unique handler.** The handler installed by `configure_logging` carries the attribute `_phronesis_managed = True`. Each call removes the previous managed ones and adds a new one: **idempotent**.
- **JSON by default.** Production is the default case; development opts in with `structured=False`.
- **`ContextLoggerAdapter` with call-site priority.** On key conflict, what the call-site passes in `extra=` wins over the adapter's fixed context.
- **`NullHandler` in `phronesis/__init__.py`.** Guarantees that if the user does not call `configure_logging`, no "no handlers" warnings appear.

<div align="center">

## 📊 Diagrams

</div>

Idempotent setup:

```
   App                  configure_logging          phronesis logger             Handler
    |                          |                          |                       |
    | configure_logging(level) |                          |                       |
    |------------------------->|                          |                       |
    |                          | setLevel(level)          |                       |
    |                          |------------------------->|                       |
    |                          | remove old managed       |                       |
    |                          |------------------------->|                       |
    |                          | build StreamHandler      |                       |
    |                          |--------------------------------------+---------->|
    |                          | addHandler(Handler)      |                       |
    |                          |------------------------->|                       |
    |                          |                          |                       |
    | --- subsequent calls are idempotent ----------------                        |
```

Context merge (call-site wins):

```
   Caller            ContextLoggerAdapter         Logger
     |                       |                       |
     | log.info("msg",       |                       |
     |   extra={k2: v2})     |                       |
     |---------------------->|                       |
     |                       | merge fixed {k1:v1}   |
     |                       |   with {k2:v2}        |
     |                       | (call-site overrides) |
     |                       |---------------------->|
```

<div align="center">

## 📋 Examples

</div>

```python
from phronesis._internal.logging import configure_logging, get_logger

configure_logging(level=10, structured=True)   # DEBUG, JSON
log = get_logger("phronesis.http")
log.info("http request", extra={"method": "GET", "url": "/v1/x"})
```

```python
from phronesis._internal.logging import get_logger_with_context

log = get_logger_with_context("phronesis.agent", agent_id="AID-42", run_id="r-001")
log.info("step start", extra={"step": "plan"})
# emits: agent_id=AID-42, run_id=r-001, step=plan
```

<div align="center">

## ⚠️ Pitfalls

</div>

- Calling `configure_logging` **n** times does not accumulate handlers; but calling it concurrently from two threads without synchronization can leave an intermediate state. Configure once at startup.
- `ContextLoggerAdapter` is a `logging.LoggerAdapter`: to inject into `extra`, the formatter must consume `record.__dict__` (both formatters in this package do).
- The level is applied to the `phronesis` root logger, not to handlers: handlers inherit.
- Loggers outside `phronesis.*` are **not** touched by `configure_logging`.

<div align="center">

## 🧪 Testing

</div>

Tests live under `tests/_internal/logging/`:

- Idempotence: after N calls, exactly one managed handler.
- A previously installed `NullHandler` is not counted as managed.
- Context merge: call-site wins over fixed context.
- Formatters: JSON is parseable; human-readable contains the expected fields.

<div align="center">

## 🚦 Quality gates

</div>

```
uv run ruff format src/phronesis/_internal/logging tests/_internal/logging
uv run ruff check src/phronesis/_internal/logging tests/_internal/logging
uv run mypy src/phronesis/_internal/logging
uv run pytest tests/_internal/logging -q
```
