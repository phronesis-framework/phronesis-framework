#

<div align="center">
  <img src="../../../public/assets/lockup/lockup-horizontal-dark.svg" alt="Phronesis Framework" width="60%" />
</div>

<div align="center">

# Phronesis Framework — `_internal.typing`

</div>

<div align="center">
  Shared typing primitives: JSON, <code>Result</code>, <code>Maybe</code>, <code>MISSING</code>, semantic NewTypes, structural protocols, streaming, and binary payloads.
</div>

<div align="center">
  <a href="../index.md">internal</a> ·
  <a href="../../index.md">docs</a> ·
  <a href="../../../src/phronesis/_internal/typing/">source</a> ·
  <a href="../../../tests/_internal/typing/">tests</a>
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

`typing` is the base of the internal dependency graph. It provides the typed vocabulary the rest of the framework reuses without reinventing:

- Model **optional values** without colliding with semantically valid `None` (`Maybe`, `MISSING`).
- Model **typed success/failure** without using exceptions for control flow (`Result`).
- Tag **domain quantities** (tokens, seconds, cost) so mypy catches accidental mixing.
- Declare minimal **structural contracts** (`SupportsJson`, `Identifiable`).
- Define uniform **streaming** and **binary** primitives for the whole framework.

It depends on nothing. Any `_internal` subpackage may import it freely.

<div align="center">

## 🏗️ Architecture

</div>

```
   json.py ---> protocols.py
      \
       \---> streaming.py

   binary.py   result.py   maybe.py   sentinels.py   newtypes.py
   (independent leaf modules)
```

Each file covers one orthogonal responsibility. There is no cross-hierarchy: `__init__.py` aggregates and re-exports. The only internal dependency is `protocols.py` and `streaming.py` referencing `JsonValue` from `json.py`.

<div align="center">

## 📦 Module layout

</div>

| File | Responsibility |
|---|---|
| `json.py` | `JsonValue`, `JsonArray`, `JsonObject` — recursive type aliases. |
| `result.py` | `Ok[T]`, `Err[E]`, `Result[T, E]` — tagged union of success/failure. |
| `maybe.py` | `Some[T]`, `NOTHING`, `NothingType`, `Maybe[T]` — explicit optional. |
| `sentinels.py` | `MISSING`, `MissingType` — distinguish "not provided" from `None`. |
| `newtypes.py` | `Seconds`, `Milliseconds`, `TokenCount`, `PromptTokens`, `CompletionTokens`, `Cost`, `ByteSize`. |
| `protocols.py` | `SupportsJson`, `Identifiable` — structural contracts. |
| `streaming.py` | `StreamChunk[T]`, `Stream[T]` — primitives for streaming responses. |
| `binary.py` | `BinaryContent` — bytes tagged with `content_type`. |

<div align="center">

## 🔌 Public API

</div>

Everything is re-exported from `phronesis._internal.typing`:

```python
from phronesis._internal.typing import (
    # JSON
    JsonValue, JsonArray, JsonObject,
    # Result
    Result, Ok, Err,
    # Maybe
    Maybe, Some, NOTHING, NothingType,
    # Sentinels
    MISSING, MissingType,
    # NewTypes
    Seconds, Milliseconds,
    TokenCount, PromptTokens, CompletionTokens,
    Cost, ByteSize,
    # Protocols
    SupportsJson, Identifiable,
    # Streaming / binary
    Stream, StreamChunk, BinaryContent,
)
```

<div align="center">

## 📐 Design decisions

</div>

- **`Result` vs exceptions.** Exceptions are reserved for exceptional errors; `Result` models the normal outcome of operations that can fail in expected ways (validation, parsing, lookup).
- **`Maybe` vs `T | None`.** `Maybe` distinguishes "absent value" from "present value that is `None`". Useful when `None` is a legitimate domain value.
- **`MISSING` vs `None` defaults.** In function signatures with optional arguments where `None` is a valid value: `def f(x: int | None | MissingType = MISSING)`.
- **`NewType` instead of bare `int`/`float`.** Prevents passing `Seconds` where `Milliseconds` is expected. Zero runtime cost.
- **`StreamChunk.sequence`.** Numbering chunks allows re-ordering and gap detection when the transport does not guarantee order.

<div align="center">

## 📊 Diagrams

</div>

Result as a tagged union:

```
      Result[T, E]
       /        \
      v          v
   Ok[T]       Err[E]
   value: T    error: E
```

Maybe as a tagged union:

```
      Maybe[T]
       /     \
      v       v
   Some[T]   NOTHING : NothingType
   value: T
```

<div align="center">

## 📋 Examples

</div>

```python
from phronesis._internal.typing import Result, Ok, Err

def parse_int(raw: str) -> Result[int, str]:
    try:
        return Ok(int(raw))
    except ValueError:
        return Err(f"not an int: {raw!r}")

match parse_int("42"):
    case Ok(value):
        print(value)
    case Err(error):
        print(error)
```

```python
from phronesis._internal.typing import MISSING, MissingType

def update(*, name: str | None | MissingType = MISSING) -> None:
    if name is MISSING:
        ...  # do not touch the field
    elif name is None:
        ...  # clear the field
    else:
        ...  # assign
```

```python
from phronesis._internal.typing import Seconds, Milliseconds

timeout: Seconds = Seconds(30.0)
elapsed: Milliseconds = Milliseconds(1500)
# timeout + elapsed  # mypy: error, incompatible types
```

<div align="center">

## ⚠️ Pitfalls

</div>

- `NOTHING` and `MISSING` are **singletons**: always compare with `is`, never `==`.
- `bool(NOTHING)` and `bool(MISSING)` are `False`, but **do not rely** on truthiness for semantic distinction.
- `Result` is a `TypeAlias`, not a class: you cannot `isinstance(x, Result)`. Use `isinstance(x, Ok)` / `isinstance(x, Err)` or `match`.
- `NewType` is nominal only: at runtime it stays the base type. mypy is what prevents mixing.

<div align="center">

## 🧪 Testing

</div>

Tests live under `tests/_internal/typing/`, one file per module. They cover:

- Type equivalences (`assert_type`) where applicable.
- Behavior of `__bool__`, `__repr__`, and `is`-comparisons on sentinels.
- Construction and exhaustive matching of `Result` and `Maybe`.

<div align="center">

## 🚦 Quality gates

</div>

```
uv run ruff format src/phronesis/_internal/typing tests/_internal/typing
uv run ruff check src/phronesis/_internal/typing tests/_internal/typing
uv run mypy src/phronesis/_internal/typing
uv run pytest tests/_internal/typing -q
```
