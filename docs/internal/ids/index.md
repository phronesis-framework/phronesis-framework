#

<div align="center">
  <img src="../../../public/assets/lockup/lockup-horizontal-dark.svg" alt="Phronesis Framework" width="60%" />
</div>

<div align="center">

# Phronesis Framework — `_internal.ids`

</div>

<div align="center">
  Stable identifiers for declared entities: <code>Id</code> base class, deterministic derivation, generic generator, and canonical validation.
</div>

<div align="center">
  <a href="../index.md">internal</a> ·
  <a href="../../index.md">docs</a> ·
  <a href="../../../src/phronesis/_internal/ids/">source</a> ·
  <a href="../../../tests/_internal/ids/">tests</a>
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

Every first-class entity in the framework (tools, agents, pipelines…) needs a **stable identifier** that is derivable and serializable. The `ids` package provides:

- An immutable `Id` base class with `canonical` (validated string) and `short` (`<PREFIX>-XXXXXXXX`).
- A validator for the canonical format (lowercase, dot-separated, `[a-z_][a-z0-9_]*` segments).
- A deterministic deriver from Python functions (`module.qualname`).
- A generic generator parameterized by the concrete `Id` subclass.

Concrete subclasses (`ToolId`, `AgentId`, …) live in their own packages and only define `prefix`.

<div align="center">

## 🏗️ Architecture

</div>

```
   validator.py ----> id.py ----+
                                 \
                                  +---> generator.py
                                 /
   derivation.py ---------------+
```

- `validator.py` depends on nothing; pure string validation.
- `id.py` consumes `validator.py` in `__post_init__`.
- `derivation.py` depends on nothing; pure function.
- `generator.py` composes `id.py` + `derivation.py`.

<div align="center">

## 📦 Module layout

</div>

| File | Responsibility |
|---|---|
| `id.py` | Frozen dataclass `Id` with `canonical` and `short` property (SHA-256 prefix). |
| `validator.py` | `CanonicalIdValidator.validate(value)` — regex and clear error message. |
| `derivation.py` | `canonical_from_function(fn) -> str` — lowercased `module.qualname`. |
| `generator.py` | `IdGenerator[IdT]` — factory `.from_function()` / `.from_canonical()`. |

<div align="center">

## 🔌 Public API

</div>

```python
from phronesis._internal.ids import (
    Id,
    IdGenerator,
    CanonicalIdValidator,
    canonical_from_function,
)
```

Usage pattern in a consumer package (`tools/`, for example):

```python
from dataclasses import dataclass
from typing import ClassVar
from phronesis._internal.ids import Id, IdGenerator

@dataclass(frozen=True, slots=True)
class ToolId(Id):
    prefix: ClassVar[str] = "TID"

tool_ids = IdGenerator(ToolId)
```

<div align="center">

## 📐 Design decisions

</div>

- **`canonical` as string, not UUID.** Human stability: two identical definitions produce the same id on any machine, at any time.
- **`short` derived, not stored.** `short` is display-only; never used as a primary key. The real identity is `canonical`.
- **`prefix` as a required `ClassVar`.** Constructing `Id` directly fails in `__post_init__`; this forces a domain-typed subclass.
- **Restrictive regex.** The canonical format disallows uppercase, dashes, and Unicode: minimizes ambiguity between visually similar identifiers.
- **`canonical_from_function` lowercased.** Guarantees the same id for `Foo.bar` and `foo.bar` (Python is case-sensitive, but the canonical id is not).

<div align="center">

## 📊 Diagrams

</div>

Type hierarchy:

```
                   +-----------------------+
                   |          Id           |   <<frozen dataclass>>
                   +-----------------------+
                   | + canonical: str      |
                   | + prefix: ClassVar    |
                   | + short: str          |
                   | + __post_init__()     |
                   +-----+-----------+-----+
                         ^           ^
                         |           |
                   +-----+----+   +--+-----+
                   |  ToolId  |   | AgentId |
                   |  TID     |   |  AID    |
                   +----------+   +---------+

                +---------------------------+
                |   IdGenerator[IdT]        |
                +---------------------------+
                | + from_function(fn) IdT   |
                | + from_canonical(s)  IdT  |
                +-------------+-------------+
                              |
                              v  creates
                              Id subclasses
```

<div align="center">

## 📋 Examples

</div>

```python
from phronesis._internal.ids import IdGenerator, Id
from dataclasses import dataclass
from typing import ClassVar

@dataclass(frozen=True, slots=True)
class ToolId(Id):
    prefix: ClassVar[str] = "TID"

def my_tool() -> None: ...

ids = IdGenerator(ToolId)
tid = ids.from_function(my_tool)

print(tid.canonical)  # "my_module.my_tool"
print(tid.short)      # "TID-AB12CD34"
print(str(tid))       # "my_module.my_tool"
```

```python
from phronesis._internal.ids import CanonicalIdValidator

CanonicalIdValidator.validate("phronesis._internal.ids")  # OK
CanonicalIdValidator.validate("Bad-Id")                   # ValueError
```

<div align="center">

## ⚠️ Pitfalls

</div>

- Subclasses of `Id` **must** declare a non-empty `prefix`; otherwise `__post_init__` raises `TypeError`.
- `Id` is `frozen=True` and `slots=True`: no runtime attribute assignment.
- `from_function` uses `__qualname__`: lambdas yield useless ids (`<lambda>`); use `from_canonical` in that case.
- Two functions in different modules with the same `qualname` produce **different** ids (because of `module.qualname`).

<div align="center">

## 🧪 Testing

</div>

Tests live under `tests/_internal/ids/`:

- Canonical validation: acceptance and rejection cases.
- Derivation: deterministic equality for the same function.
- Generator: typing and construction from both sources.
- `short`: stability and `<PREFIX>-[0-9A-F]{8}` format.

<div align="center">

## 🚦 Quality gates

</div>

```
uv run ruff format src/phronesis/_internal/ids tests/_internal/ids
uv run ruff check src/phronesis/_internal/ids tests/_internal/ids
uv run mypy src/phronesis/_internal/ids
uv run pytest tests/_internal/ids -q
```
