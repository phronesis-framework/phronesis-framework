#

<div align="center">
  <img src="../../public/assets/lockup/lockup-horizontal-dark.svg" alt="Phronesis Framework" width="60%" />
</div>

<div align="center">

# Phronesis Framework - `_internal`

</div>

<div align="center">
  Shared infrastructure that underpins the rest of the framework: typing, identity, logging, HTTP, retry, and concurrency.
</div>

<div align="center">
  <a href="../index.md">docs</a> ·
  <a href="../../src/phronesis/_internal/">source</a> ·
  <a href="../../tests/_internal/">tests</a>
</div>

<div align="center">

[![Status](https://img.shields.io/badge/status-WIP-orange)]()
[![Coverage](https://img.shields.io/badge/coverage-100%25-brightgreen)]()
[![Python](https://img.shields.io/badge/python-3.11+-blue?logo=python&logoColor=white)]()

</div>

---

<div align="center">

## 🎯 Purpose

</div>

The `_internal` package groups the framework's **shared, private** infrastructure. It does not expose any public API directly: the rest of the modules consume it internally.

Each subpackage covers one isolated concern, has its own `__init__.py`, and mirrors its tests under `tests/_internal/`.

<div align="center">

## 🏗️ Architecture

</div>

- `typing` depends on nothing (base of the graph).
- `logging` depends only on `typing`.
- `http`, `retry`, and `concurrency` depend on `logging` for structured emission.
- `retry` and `http` are natural consumers of each other (retry wraps HTTP calls), but the `retry` module is **transport-agnostic**.

<div align="center">

## 📦 Modules

</div>

| Module | Status | Description | Doc |
|---|---|---|---|
| `typing` | implemented | Typing primitives: `JSON`, `Result`, `Maybe`, `MISSING`, NewTypes, protocols, streaming, binary | [typing/](./typing/index.md) |
| `ids` | implemented | Identifiers: base `Id`, deterministic derivation, generator, validators | [ids/](./ids/index.md) |
| `logging` | implemented | Structured and human-readable loggers, context adapter, factory, idempotent config | [logging/](./logging/index.md) |
| `http` | implemented | Async HTTP client, per-phase timeouts, error hierarchy, sensitive-header redaction | [http/](./http/index.md) |
| `retry` | implemented | `@retry` decorator, backoffs (fixed and exponential with jitter), attempt history | [retry/](./retry/index.md) |
| `concurrency` | implemented | `run_sync`, `gather_all` with policies (`FailFast`/`BestEffort`), partial failures | [concurrency/](./concurrency/index.md) |

<div align="center">

## 🔗 Dependencies

</div>

External (declared in `pyproject.toml`):

- `httpx` - HTTP transport (only used by `_internal/http`).

Internal: see the diagram above.

<div align="center">

## 🚦 Quality gates

</div>

Same as the repo:

```
uv run ruff format src/phronesis/_internal tests/_internal
uv run ruff check src/phronesis/_internal tests/_internal
uv run mypy src/phronesis/_internal
uv run pytest tests/_internal -q
```

All must pass before committing.
