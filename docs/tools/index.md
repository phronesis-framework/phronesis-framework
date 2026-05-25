#

<div align="center">
  <img src="../../public/assets/lockup/lockup-horizontal-dark.svg" alt="Phronesis Framework" width="60%" />
</div>

<div align="center">

# Phronesis Framework - `tools`

</div>

<div align="center">
  Declarative <code>@tool</code> decorator that turns Python callables into LLM-callable, schema-validated, provider-adaptable units with two-channel error handling, type-driven Context injection, and a scoped registry.
</div>

<div align="center">
  <a href="../index.md">docs</a> ·
  <a href="../../src/phronesis/tools/">source</a> ·
  <a href="../../tests/tools/">tests</a>
</div>

<div align="center">

[![Status](https://img.shields.io/badge/status-stable-green)]()
[![Coverage](https://img.shields.io/badge/coverage-100%25-brightgreen)]()
[![Python](https://img.shields.io/badge/python-3.11+-blue?logo=python&logoColor=white)]()
[![Pydantic](https://img.shields.io/badge/pydantic-v2-e92063?logo=pydantic&logoColor=white)]()
[![Tests](https://img.shields.io/badge/tests-270-blue)]()

</div>

---

<div align="center">

## 🎯 Purpose

</div>

A `@tool`-decorated Python function becomes a **first-class unit** an LLM-driven runtime can:

1. **Discover** through a registry.
2. **Introspect** via a canonical JSON schema (and per-provider variants).
3. **Call** with validated arguments.
4. **Recover from** through a structured error channel.

The goal is to make tool authoring **boring**: the developer writes a function with type hints and a docstring; the framework handles registration, schema, validation, error mapping, provider adaptation, and runtime injection of execution context.

What the user writes:

```python
from phronesis import tool

@tool
def add(a: int, b: int) -> int:
    """Sum two integers."""
    return a + b
```

What the framework derives for free:

- A stable **id** (`phronesis.tools.add`) and an LLM-facing **name** (`add`).
- A canonical **input schema** (`{type: object, properties: {a: int, b: int}, required: [a, b]}`).
- A **validator** that rejects wrong types with `ToolValidationError` before the function runs.
- **Provider-adapted schemas** for Anthropic (`{name, description, input_schema}`) and OpenAI Chat Completions (`{type: function, function: {...}}`), cached on first request.
- **Registration** into the active registry (global by default, scoped via `tool_scope()`).
- A `Tool` callable with `invoke(args, context=...)` for runtime use and `__call__` for direct programmatic / test use.

Non-goals (deliberately):

- The runtime loop (scheduling, retries, streaming) - lives in a future `runtime/` module.
- Effect enforcement (rate limits, approval flows) - lives in a future `policy/` module.
- Serialization of `ToolError` into a provider-specific tool-result message - runtime's responsibility.

<div align="center">

## 🏗️ Architecture

</div>

The module is split into a **pure-data side** (frozen, serializable types) and a **callable side** (the `Tool` wrapper and its helpers). The decorator stitches them together; everything else is composable.

```
                              +------------------+
                              |   decorator.py   |  @tool / @tool(...)
                              +------------------+
                                       |
                +----------------------+----------------------+
                |                      |                      |
                v                      v                      v
        +---------------+      +---------------+      +---------------+
        |   spec.py     |      |    tool.py    |      |  registry.py  |
        |   ToolSpec    |      |    Tool       |      |  tool_scope   |
        +---------------+      +---------------+      +---------------+
                ^                      |                      ^
                |                      |                      |
                |        +-------------+-------------+        |
                |        |             |             |        |
                |        v             v             v        |
                |  +-----------+ +-----------+ +-----------+  |
                |  |validation | | schema    | | providers/|  |
                |  |   .py     | |   .py     | |  base     |  |
                |  +-----------+ +-----------+ |  anthropic|  |
                |        |             |       |  openai   |  |
                |        v             v       +-----------+  |
                |  +-----------+ +-----------+                |
                |  |single_    | |markers.py |                |
                |  |model.py   | +-----------+                |
                |  +-----------+                              |
                |        |                                    |
                |        v                                    |
                |  +-----------+                              |
                |  |injection  |                              |
                |  |   .py     |                              |
                |  +-----------+                              |
                |                                             |
        +---------------+   +---------------+   +-----------+ |
        |   effects     |   |   errors      |   | tool_id   | |
        |     .py       |   |     .py       |   |    .py    | |
        +---------------+   +---------------+   +-----------+ |
                                                              |
                              +------------------+            |
                              |   discover.py    |------------+
                              | (imports submods |
                              |  to trigger      |
                              |  registrations)  |
                              +------------------+
```

**Pure-data side** (no executable behavior, JSON-serializable):

- `tool_id.py` - `ToolId`, `ToolName`.
- `effects.py` - `ToolEffect` enum.
- `spec.py` - `ToolSpec` frozen dataclass with `MappingProxyType` schemas.
- `errors.py` - `ToolError` hierarchy + `auto_map_exception`.

**Callable side** (orchestration):

- `tool.py` - `Tool` wrapper with `__call__`, `invoke`, `get_schema`, `schema`.
- `decorator.py` - `@tool` entry point.
- `registry.py` - `_ToolRegistry` + `tool_scope()` + `current_registry()`.
- `discover.py` - `discover(package)` recursive importer.

**Helpers** (consumed by `tool.py` and the decorator):

- `injection.py` - `detect_context_param` by type.
- `single_model.py` - `get_single_model` detection.
- `validation.py` - `build_validator` (delegates to `single_model` when applicable).
- `schema.py` - `build_canonical_schema` (delegates to `single_model` when applicable).
- `markers.py` - `Annotated` helpers re-exporting `annotated_types`.

**Provider adapters**:

- `providers/base.py` - `ProviderAdapter` Protocol.
- `providers/anthropic.py` - `AnthropicAdapter`.
- `providers/openai.py` - `OpenAIAdapter`.
- `providers/__init__.py` - `get_adapter(name)` lookup + `UnsupportedProviderError`.

<div align="center">

## 📦 Module layout

</div>

| File | Responsibility | Public symbols |
|---|---|---|
| `decorator.py` | `@tool` / `@tool(...)` decorator; assembles `ToolSpec`; registers into the active registry. | `tool` |
| `tool.py` | `Tool` callable: argument binding, validation, Context injection, two-channel errors, schema cache, override. | `Tool` |
| `spec.py` | Frozen, JSON-serializable description of a tool. No function reference. | `ToolSpec` |
| `tool_id.py` | Identifier types: internal (`ToolId`, prefix `TID`) and LLM-facing (`ToolName`). | `ToolId`, `ToolName`, `tool_id_generator` |
| `effects.py` | Closed, framework-owned vocabulary of declarable side-effects. | `ToolEffect` |
| `errors.py` | LLM-facing error hierarchy; auto-mapper for standard exceptions. | `ToolError`, `ToolValidationError`, `ToolNotFoundError`, `ToolTimeoutError`, `ToolPermissionError`, `ToolHTTPError`, `DuplicateToolError`, `ToolDefinitionError`, `UnsupportedProviderError`, `SchemaDegradationWarning`, `auto_map_exception` |
| `injection.py` | Detection of `Context`-typed parameters for runtime injection (by type, not by name). | `detect_context_param` |
| `markers.py` | Re-exports of `annotated_types` markers and a `Pattern` helper for `Annotated`-based schema augmentation. | `MinLen`, `MaxLen`, `Ge`, `Gt`, `Le`, `Lt`, `Pattern` |
| `schema.py` | Canonical JSON schema generation (Pydantic v2 backed, ref-inlined, null-stripped, descriptions from docstring or `Annotated`). | `build_canonical_schema` |
| `single_model.py` | Detection of single-`BaseModel`-input tools and helpers used by `validation` and `schema`. | `get_single_model` |
| `validation.py` | Pydantic-backed kwargs validator; delegates to the declared model for single-model tools. | `build_validator` |
| `registry.py` | Thread-safe `_ToolRegistry`, process-wide default, async-safe `tool_scope()` via `ContextVar`. | `tool_scope`, `current_registry` |
| `discover.py` | Recursive package import that triggers `@tool` decorations; broken submodules warn but do not abort. | `discover` |
| `providers/base.py` | `ProviderAdapter` Protocol (`name` + `adapt(canonical, *, spec)`). | `ProviderAdapter` |
| `providers/anthropic.py` | Anthropic Messages-API shape. | `AnthropicAdapter` |
| `providers/openai.py` | OpenAI Chat Completions function shape. | `OpenAIAdapter` |
| `providers/__init__.py` | Closed adapter registry, `get_adapter(name)`. | `get_adapter` |
| `__init__.py` | Public re-exports. | (see Public API) |

<div align="center">

## 🔌 Public API

</div>

### Imports

```python
from phronesis.tools import (
    # decorator and callable wrapper
    tool, Tool,
    # data
    ToolSpec, ToolId, ToolName, ToolEffect,
    # runtime
    Context,
    # registry and discovery
    tool_scope, current_registry, discover,
    # errors
    ToolError,
    ToolValidationError, ToolNotFoundError, ToolTimeoutError,
    ToolPermissionError, ToolHTTPError, DuplicateToolError,
    ToolDefinitionError, UnsupportedProviderError,
    SchemaDegradationWarning, auto_map_exception,
)
```

Top-level convenience (six most-used names):

```python
from phronesis import tool, Context, ToolEffect, ToolError, tool_scope, discover
```

### `@tool`

```python
@overload
def tool(fn: Callable[..., Any], /) -> Tool: ...

@overload
def tool(
    *,
    name: str | None = None,
    id: str | None = None,
    description: str | None = None,
    effects: Iterable[ToolEffect] | None = None,
    version: str | None = None,
    lazy: bool = False,
) -> Callable[[Callable[..., Any]], Tool]: ...
```

| Argument | Inferred from | Override effect |
|---|---|---|
| `name` | `fn.__name__` | LLM-facing handle. Must be unique within the registry only by `id`, not by name. |
| `id` | `phronesis._internal.ids.derivation.canonical_from_function(fn)` | Stable internal identifier. Lowercase, dot-separated. Collisions raise `DuplicateToolError`. |
| `description` | `inspect.getdoc(fn)` | Free-form text sent to the LLM. |
| `effects` | `frozenset()` | Declarative tags (`ToolEffect`) for downstream policy modules. |
| `version` | `"0.1.0"` | Semver-style string; informational. |
| `lazy` | `False` | When `True`, schema is built on first `get_schema()` instead of at decoration time. |

### `Tool`

```python
class Tool:
    spec: ToolSpec
    is_async: bool

    def __call__(self, *args, **kwargs) -> Any | Coroutine: ...
    def invoke(
        self,
        args: dict[str, Any] | None = None,
        *,
        context: Context | None = None,
    ) -> Any | Coroutine: ...
    def get_schema(self, provider: str | None = None) -> dict[str, Any]: ...
    def schema(self, factory: Callable[[], dict[str, Any]]) -> Callable[[], dict[str, Any]]: ...
```

| Method | Purpose | Validates? | Injects Context? |
|---|---|---|---|
| `__call__(*a, **kw)` | Direct call; testing / programmatic use. | yes | no - pass it as a kwarg by its real name |
| `invoke(args, *, context=ctx)` | Runtime entry point; `args` is the LLM-provided dict. | yes | yes - by type |
| `get_schema(provider=None)` | Canonical or provider-adapted schema. | n/a | n/a |
| `schema(factory)` | Decorator to override the canonical schema (paired decorator). | n/a | n/a |

### `tool_scope`

```python
@contextmanager
def tool_scope() -> Iterator[_ToolRegistry]:
    """Activate an isolated registry for the duration of the `with` block."""
```

`tool_scope()` swaps the active registry in a `ContextVar`, so concurrent async scopes do not see each other's tools. The previous registry is restored on exit, even on exception.

### `current_registry`

```python
def current_registry() -> _ToolRegistry: ...
```

Returns the registry currently active in the calling async context. Useful for libraries that want to enumerate tools without forcing a scope.

`_ToolRegistry` exposes:

| Method | Purpose |
|---|---|
| `register(tool)` | Insert under `tool.spec.id.canonical`. Idempotent for the same instance; raises `DuplicateToolError` for a different instance under an existing id. |
| `lookup(tool_id)` | Returns the `Tool` registered under `tool_id` (`ToolId` or `str`). Raises `ToolNotFoundError` if absent. |
| `all()` | Snapshot tuple of every registered tool. |
| `clear()` | Remove every tool. Used in tests; not a general-purpose runtime operation. |

### `discover`

```python
def discover(package: str) -> None: ...
```

Recursively imports every submodule of `package`. Submodules whose import raises any `Exception` emit a `UserWarning` and are skipped. A missing root package propagates `ModuleNotFoundError`.

### `auto_map_exception`

```python
def auto_map_exception(exc: BaseException) -> ToolError | None: ...
```

Maps a closed allowlist of standard exceptions to the appropriate `ToolError`. Returns `None` for anything outside the allowlist so the runtime can apply its own policies.

| Input | Output |
|---|---|
| `ToolError` (any subclass) | passes through unchanged |
| `FileNotFoundError` | `ToolNotFoundError` with `details={"path": filename}` |
| `PermissionError` | `ToolPermissionError` with `details={"path": filename}` |
| `TimeoutError` / `asyncio.TimeoutError` (alias in 3.11+) | `ToolTimeoutError` |
| `pydantic.ValidationError` | `ToolValidationError` with `details={"errors": [...]}` |
| `httpx.HTTPStatusError` with `4xx` status | `ToolHTTPError` with `details={"status_code", "url"}` |
| anything else | `None` |

<div align="center">

## 📐 Design decisions

</div>

| Decision |
|---|
| `@tool` accepts both `@tool` (bare) and `@tool(...)` forms via a single `overload`-typed function. |
| Sync and async callables are first-class; `Tool.is_async` is exposed; `__call__` returns the coroutine for async tools. |
| `name` defaults to `fn.__name__`; `description` defaults to `inspect.getdoc(fn)` (empty string when missing). |
| Two identifiers per tool: internal `ToolId` (stable, validator-checked) and `ToolName` (LLM-facing, free string). |
| `id` is inferred from `phronesis._internal.ids.derivation.canonical_from_function`; explicit `id=` overrides. |
| Spec (data) and tool (callable) are split: `ToolSpec` is frozen and JSON-serializable; `Tool.spec` exposes it. |
| Process-wide default registry plus async-safe `tool_scope()` via `ContextVar`. |
| Re-registering the same `Tool` instance is idempotent; different instance under existing id raises `DuplicateToolError`. |
| `discover()` is opt-in; explicit imports remain the primary path. Broken submodules warn, do not abort. |
| Effects are declarative tags on the spec; enforcement lives elsewhere. |
| Effect vocabulary is **closed** and framework-owned: users cannot invent new effects. |
| Two input shapes: flat parameters (90% case) and single `BaseModel` (10% case). Auto-detected. |
| Two error channels: `ToolError` -> serialized to LLM; everything else -> runtime policy. |
| Conservative auto-mapping: a small, closed allowlist maps standard exceptions to `ToolError`. |
| `Context` is injected by **type**, not by name. Any parameter annotated as `Context` (or subclass) qualifies. |
| MVP `Context` carries `run_id`, `agent_id`, `session_id`, `trace_id`, `logger`, `budget`, `deadline`, `metadata`. |
| `Context` is a frozen dataclass with `MappingProxyType` metadata - immutable from the tool's perspective. |
| `Context` does **not** carry mutable state, the tool registry, or output channels. |
| Schema is generated automatically; total override via `@tool.schema`; no partial override. |
| Per-parameter descriptions: Google-style docstring `Args:`, overridable by `Annotated[T, "..."]` string metadata. |
| `Annotated` markers (re-exported from `annotated_types`) control constraints: `Ge`, `Gt`, `Le`, `Lt`, `MinLen`, `MaxLen`, `Pattern`. |
| LLM-aware type translation: `$ref` inlined; `null` dropped from optional unions. |
| Provider adapters preserve canonical structure; degradation emits `SchemaDegradationWarning`. |
| Canonical schema generated **eagerly** at decoration (unless `lazy=True`); provider schemas built lazily and cached. |
| `Tool.get_schema(provider=None)` returns the canonical dict; `provider="anthropic" \| "openai"` returns the adapted dict. |
| `ToolValidationError` carries only the **affected parameter's** sub-schema in `details.expected_schema`, never the whole tool schema. |

<div align="center">

## 📊 Diagrams

</div>

### `ToolError` hierarchy

```
                          BaseException
                                |
                          Exception
                                |
                           ToolError                       [code = "tool_error"]
                                |
   +--------+--------+--------+-+------+--------+--------+--------+
   |        |        |        |        |        |        |        |
   v        v        v        v        v        v        v        v
Validation NotFound Timeout Permission HTTP   Duplicate Definition Unsupported
 Error      Error    Error    Error    Error    Tool      Error    Provider
                                                Error              Error

   |        |        |        |        |        |        |        |
   v        v        v        v        v        v        v        v
"tool_   "tool_   "tool_   "tool_   "tool_   "duplicate "tool_   "unsupported
 validation not_     timeout"  permission http_     _tool"    definition  _provider"
 _error"   found"            _denied"   error"             _error"

(Independent: SchemaDegradationWarning inherits from UserWarning, not ToolError.)
```

### Tool invocation flow (sync, runtime entry via `invoke`)

```
   Runtime                       Tool                       Wrapped fn
      |                            |                             |
      |---- invoke(args, ctx) ---->|                             |
      |                            |                             |
      |                  +---------+---------+                   |
      |                  | single-model?     |                   |
      |                  |  yes -> wrap args |                   |
      |                  |  no  -> pass thru |                   |
      |                  +---------+---------+                   |
      |                            |                             |
      |                  +---------v---------+                   |
      |                  |  validator(args)  |                   |
      |                  +---------+---------+                   |
      |                            |                             |
      |          invalid  +--------+--------+   valid            |
      |  <-- ToolValidationError    |                            |
      |                            v                             |
      |                  +-------------------+                   |
      |                  | inject Context    |  by type, if any  |
      |                  +---------+---------+                   |
      |                            |                             |
      |                            |--- fn(**validated) -------> |
      |                            |                             |
      |                            |    +------+------+------+   |
      |                            |    |return| raise| raise |  |
      |                            |    |value |ToolE | other |  |
      |                            |    +---+--+---+--+---+---+  |
      |                            |        |      |      |      |
      |                            | <------+------+------+------|
      |                            |        |      |      |      |
      |                            |        |      |      v      |
      |                            |        |      |  auto_map?  |
      |                            |        |      |    /     \  |
      |                            |        |      |  yes      no|
      |                            |        |      v   v       v |
      |                            |       value ToolE Mapped Raw |
      |                            |             pass  ToolE  exc |
      |                            |             thru          |  |
      |  <-------------------------|                              |
      |       value or exception                                  |
```

Async tools follow the exact same path; the only difference is `invoke` returns a coroutine. `asyncio.CancelledError` is **never** caught: it always propagates.

### Schema generation pipeline

```
   function signature
          |
          v
   +------------------+
   | get_single_model |---- yes ----+
   +------------------+             |
          | no                      v
          v                +---------------+
   +---------------+       | model         |
   | inspect       |       | .model_json_  |
   | .signature +  |       |  schema()     |
   | get_type_hints|       +-------+-------+
   +-------+-------+               |
           |                       |
           v                       |
   +-------------------+           |
   | filter Context    |           |
   | param             |           |
   +---------+---------+           |
             |                     |
             v                     |
   +-------------------+           |
   | pydantic.         |           |
   | create_model +    |           |
   | Field(desc=...)   |           |
   +---------+---------+           |
             |                     |
             v                     |
   +-------------------+           |
   | model.model_json_ |           |
   | schema()          |           |
   +---------+---------+           |
             |                     |
             +----------+----------+
                        |
                        v
                +-------------------+
                | _inline_refs      |
                +---------+---------+
                          |
                          v
                +-------------------+
                | _strip_null_from_ |
                | optional          |
                +---------+---------+
                          |
                          v
                  canonical schema
                          |
        +-----------------+-----------------+
        |                 |                 |
        v                 v                 v
   get_schema       get_schema(           get_schema(
   (None) -->       provider="           provider="
   canonical        anthropic")          openai")
                         |                    |
                         v                    v
                   AnthropicAdapter     OpenAIAdapter
                         |                    |
                         v                    v
                   {name, description,  {type: "function",
                    input_schema}        function: {...}}
                         |                    |
                         v                    v
                    cached on Tool      cached on Tool
```

### Registry scoping via `ContextVar`

```
                 +------------------+
                 |  _global_        |   default _ToolRegistry
                 |   registry       |
                 +--------+---------+
                          ^
                          | active by default
                          |
                 +--------+---------+
                 | _active_registry |   ContextVar
                 |   (ContextVar)   |
                 +--------+---------+
                          |
                          | swapped on enter
                          v
       +------------------+------------------+
       |                                     |
       v                                     v
   tool_scope() enter                tool_scope() exit
   (push scoped registry)            (reset token)
       |                                     ^
       |                                     |
       +-------------+-----------+-----------+
                     |
                     v
         async block sees the scoped
         registry; sibling async tasks
         outside the with block keep
         seeing the previous one.
```

### Decorator flow

```
   @tool                  @tool(...)
      |                       |
      v                       v
   tool(fn)              tool(name=..., ...)
      |                       |
      |                       v
      |                  returns decorator
      |                       |
      |                       v
      |                  decorator(fn)
      |                       |
      +-----------+-----------+
                  |
                  v
        +-------------------+
        | derive id, name,  |
        | description,      |
        | effects, version  |
        +---------+---------+
                  |
                  v
        +-------------------+
        | build canonical   |
        | schema unless     |
        | lazy=True         |
        +---------+---------+
                  |
                  v
        +-------------------+
        | construct         |
        | ToolSpec (frozen) |
        +---------+---------+
                  |
                  v
        +-------------------+
        | wrap fn in Tool   |
        +---------+---------+
                  |
                  v
        +-------------------+
        | current_registry  |
        | .register(tool)   |
        +---------+---------+
                  |
                  v
              returns Tool
```

### Two-channel error semantics

```
   wrapped fn raises X
            |
            v
   +-------------------+
   | isinstance(X,     |
   |   ToolError)?     |
   +---------+---------+
       /     |     \
     yes     |      no
      |      |       |
      |      |       v
      |      |   +-------------------+
      |      |   | auto_map_exception|
      |      |   |   returns?        |
      |      |   +-+---------------+-+
      |      |     |               |
      |      |   ToolError       None
      |      |     |               |
      |      |     v               v
      |      |  re-raise as     re-raise raw
      |      |  mapped error    exception
      |      |                  (runtime sees it)
      |      |
      |      v
      |  re-raise unchanged
      |  (LLM-bound channel)
      |
      +-> CancelledError, KeyboardInterrupt, SystemExit:
          never enter this path; they propagate raw.
```

<div align="center">

## 📋 Examples

</div>

### Minimal tool

```python
from phronesis import tool

@tool
def add(a: int, b: int) -> int:
    """Sum two integers."""
    return a + b

add.spec.id              # ToolId('phronesis.tools.add')
add.spec.name            # ToolName('add')
add.spec.description     # 'Sum two integers.'
add.invoke({"a": 2, "b": 3})   # 5
```

### Async tool

```python
import httpx
from phronesis import tool

@tool
async def fetch(url: str) -> str:
    """Fetch a URL and return its body."""
    async with httpx.AsyncClient() as client:
        response = await client.get(url)
        return response.text

await fetch.invoke({"url": "https://example.com"})
```

`Tool.is_async` is `True`; `invoke` returns a coroutine that you must `await`.

### Decorator with explicit overrides

```python
from phronesis import tool, ToolEffect

@tool(
    name="search-web",
    id="acme.search.web",
    description="Search the public web via SerpAPI.",
    effects=(ToolEffect.NETWORK, ToolEffect.EXPENSIVE),
    version="1.2.0",
)
def search(query: str, limit: int = 10) -> list[str]:
    ...
```

### Single-`BaseModel` input

For tools whose argument shape benefits from a richer model (custom validators, nested objects), declare a single `BaseModel` parameter. The framework treats it as the input root; the LLM still sees the **flat** field schema at the root.

```python
from pydantic import BaseModel, Field
from phronesis import tool

class JobInput(BaseModel):
    name: str
    count: int = Field(ge=1, description="Number of repeats.")
    tags: list[str] = []

@tool
def run_job(payload: JobInput) -> str:
    """Run a job N times."""
    return f"{payload.name} x {payload.count}"

run_job.get_schema()
# {"type": "object", "properties": {"name": ..., "count": ..., "tags": ...}, "required": ["name", "count"]}

run_job.invoke({"name": "alpha", "count": 4, "tags": ["a"]})   # validated into JobInput, then called
```

Mixed-parameter tools (`fn(x: int, payload: MyModel)`) fall back to the flat-parameters path: each argument is its own root property.

### `Context` injection by type

```python
from phronesis import tool, Context

@tool
def greet(name: str, ctx: Context) -> str:
    """Greet the user, tagging the trace id."""
    trace = ctx.trace_id or "?"
    return f"hi {name} [{trace}]"

# Schema does not expose ctx:
greet.get_schema()
# {"type": "object", "properties": {"name": {"type": "string"}}, "required": ["name"]}

# Runtime injects Context:
greet.invoke({"name": "alice"}, context=Context(trace_id="t-1"))   # "hi alice [t-1]"
```

The parameter name does not matter: `ctx`, `context`, `c`, `whatever` all work as long as the annotation resolves to `Context`. Direct `__call__` does **not** auto-inject - pass it as a kwarg:

```python
greet(name="alice", ctx=Context(trace_id="direct"))
```

### Two-channel error handling

```python
from phronesis import tool, ToolError, ToolValidationError

@tool
def fetch_file(path: str) -> str:
    """Read a file. Forbidden paths raise a structured error."""
    if path.startswith("/etc/"):
        raise ToolError("forbidden", details={"path": path})   # serialized to LLM

    return open(path).read()                                    # FileNotFoundError -> ToolNotFoundError (auto-mapped)

# Type-wise wrong arg: ToolValidationError raised before fn runs.
try:
    fetch_file.invoke({"path": 123})
except ToolValidationError as exc:
    print(exc.code)         # "tool_validation_error"
    print(exc.message)      # "Invalid argument 'path': Input should be a valid string"
    print(exc.details)      # {"field": "path", "expected_schema": {"type": "string"}, "got_value": 123}
```

### Provider-adapted schemas

```python
add.get_schema(provider="anthropic")
# {
#   "name": "add",
#   "description": "Sum two integers.",
#   "input_schema": {
#     "type": "object",
#     "properties": {"a": {"type": "integer"}, "b": {"type": "integer"}},
#     "required": ["a", "b"],
#     "additionalProperties": false
#   }
# }

add.get_schema(provider="openai")
# {
#   "type": "function",
#   "function": {
#     "name": "add",
#     "description": "Sum two integers.",
#     "parameters": {
#       "type": "object",
#       "properties": {"a": {"type": "integer"}, "b": {"type": "integer"}},
#       "required": ["a", "b"],
#       "additionalProperties": false
#     }
#   }
# }

add.get_schema(provider="bogus")
# raises UnsupportedProviderError(details={"provider": "bogus", "available": ["anthropic", "openai"]})
```

Each provider schema is cached after the first request.

### `Annotated` markers

```python
from typing import Annotated
from phronesis import tool
from phronesis.tools.markers import Ge, Le, MinLen, MaxLen, Pattern

@tool
def issue(
    title: Annotated[str, MinLen(1), MaxLen(120), "Short summary."],
    priority: Annotated[int, Ge(1), Le(5)] = 3,
    component: Annotated[str, Pattern(r"^[a-z][a-z0-9_-]*$")] = "core",
) -> str:
    ...
```

The string metadata in `Annotated` overrides any Google-docstring description.

### Total schema override (rare)

```python
@tool
def search(q: str) -> list[str]:
    """Search the index."""
    ...

@search.schema
def _() -> dict:
    return {
        "type": "object",
        "properties": {
            "q": {"type": "string", "minLength": 1, "description": "user query"},
            "filters": {"type": "object", "additionalProperties": {"type": "string"}},
        },
        "required": ["q"],
        "additionalProperties": False,
    }

search.get_schema()                   # overridden dict
search.get_schema(provider="openai")  # adapter runs on the override
```

The validator is **not** affected by the override (presentation only). To change validation, change the function signature or move to a single-model input.

### Scoped registry and `discover`

```python
from phronesis import tool_scope, discover, current_registry

with tool_scope() as scope:
    discover("my_app.tools")              # imports submodules; each @tool registers into `scope`
    names = [str(t.spec.name) for t in scope.all()]

# Outside the with block the global registry is active again:
current_registry() is not scope          # True
```

`discover` is the bulk-load convenience; explicit imports are still the primary path. Broken submodules emit a `UserWarning` and are skipped, so a single bad file does not abort startup:

```python
import warnings

with warnings.catch_warnings(record=True) as caught:
    warnings.simplefilter("always")
    discover("my_app.tools")

for w in caught:
    print(w.message)   # "discover: failed to import 'my_app.tools.broken': ..."
```

### Combining everything

```python
from typing import Annotated
from pydantic import BaseModel, Field
from phronesis import tool, Context, ToolEffect, ToolError, tool_scope
from phronesis.tools.markers import MinLen

class Query(BaseModel):
    q: Annotated[str, MinLen(1)]
    top_k: int = Field(default=5, ge=1, le=50)

@tool(effects=(ToolEffect.NETWORK,))
async def search(payload: Query, ctx: Context) -> list[str]:
    """Search the vector store."""
    if ctx.budget is not None and ctx.budget.remaining_tokens < payload.top_k * 100:
        raise ToolError("not enough budget", details={"top_k": payload.top_k})

    # ... call vector store; on failure auto-mapped or propagated ...
    return ["..."]

# Programmatic invocation:
result = await search.invoke({"q": "phronesis", "top_k": 3}, context=Context(trace_id="t-9"))
```

<div align="center">

## 🔗 Dependencies

</div>

### Hard dependencies (always imported)

- **`pydantic >= 2`** - validation, `create_model`, `model_json_schema`, `BaseModel`.
- **`annotated_types`** - constraint metadata for `Annotated`.

### Soft dependencies (lazy imports inside `auto_map_exception`)

- **`pydantic.ValidationError`** - already in the hard dep.
- **`httpx.HTTPStatusError`** - only imported when mapping an exception of that type; `httpx` is **not** required to use `tools`.

### Internal dependencies

| From `phronesis.tools` -> | Used for |
|---|---|
| `phronesis.context.context.Context` | type-driven injection |
| `phronesis._internal.ids.derivation.canonical_from_function` | default `id` derivation |
| `phronesis._internal.ids.id.Id` / `IdGenerator` | base for `ToolId` |

### Who depends on `phronesis.tools`

Currently nobody else in the framework consumes `phronesis.tools` directly - this module is a leaf. The future `runtime/` will be the first consumer.

<div align="center">

## ⚠️ Pitfalls

</div>

- **Direct `__call__` does not auto-inject `Context`.** Pass it as a kwarg by its real parameter name (`my_tool(name="alice", ctx=ctx)`) or use `invoke(args, context=ctx)`. The "no auto-inject on direct call" rule keeps `__call__` test-friendly and free of magic.
- **`@tool.schema` does not change validation.** Override is presentation-only. Validation always follows the function signature (or the single-`BaseModel` parameter).
- **Single-model and `Context` coexist.** A tool can declare exactly one `BaseModel` and a `Context`. Two `BaseModel` parameters disable single-model mode and fall back to the flat-parameters path.
- **`<locals>` in qualified names break id derivation.** Define tools at module level; nesting under a class or function yields ids that fail `ToolId` validation (`"a.<locals>.b"` is not lowercase-dot-separated).
- **`auto_map_exception` is a closed allowlist.** Adding a new mapped exception requires editing `errors.py`; subclassing or duck-typing will not work.
- **`tool_scope()` is per async context.** Threads not started inside the scope see the global registry. Spawn helpers inside the scope, or hand them the scoped registry explicitly.
- **`discover()` warns on broken submodules.** If you need import failures to abort startup, do not use `discover()`; import explicitly.
- **Tool name uniqueness is not enforced.** Two tools can share the same `name` if their `id` differs. Make names unique yourself if your provider requires it (Anthropic and OpenAI both do).
- **Provider schemas are cached on the `Tool` instance.** Mutating the canonical schema dict in-place after the first `get_schema(provider=...)` will not invalidate the provider cache - use `@tool.schema` (which does) or rebuild the `Tool`.
- **`Context.metadata` is a `MappingProxyType`.** Attempting to mutate it raises `TypeError` at runtime.
- **`asyncio.TimeoutError` is an alias of `TimeoutError`** since Python 3.11. The `auto_map_exception` allowlist lists `TimeoutError` once; do not add a second check for `asyncio.TimeoutError`.

<div align="center">

## 🧪 Testing

</div>

Tests mirror the source layout under `tests/tools/`:

| Test file | What it covers |
|---|---|
| `test_decorator.py` | `@tool` vs `@tool(...)` forms, inference, explicit overrides, registration side-effect. |
| `test_tool.py` | Invocation (sync/async), signature preservation, repr, validation, schema (canonical + provider + override), two-channel errors, Context injection. |
| `test_validation.py` | Pydantic-backed validation; field-scoped error `details`. |
| `test_schema.py` | Basic types, containers, optional null-strip, Literal/Enum, descriptions, `$ref` inlining, Context filtering. |
| `test_single_model.py` | Detection of single-`BaseModel` inputs, model-delegated validation, model-derived schema, interaction with `Context`. |
| `test_injection.py` | `Context` detection by type, alias names, multiple-`Context` rejection. |
| `test_registry.py` | Global registry, `tool_scope`, isolation across scopes, duplicate detection. |
| `test_discover.py` | Happy path, recursive walk, broken submodule warning, missing root, single-file module. |
| `test_errors.py` | Hierarchy, codes, serialization, `auto_map_exception` allowlist. |
| `test_effects.py`, `test_spec.py`, `test_tool_id.py`, `test_markers.py` | Data primitives. |
| `providers/test_anthropic.py` | Anthropic adapter shape contract. |
| `providers/test_openai.py` | OpenAI Chat Completions adapter shape contract. |
| `test_public_api.py` | `__all__` invariants and end-to-end smoke through `phronesis` re-exports. |

Counts:

- `tests/tools/` - **270 tests**.
- Whole repository - **508 tests**.

Common pytest patterns used:

- Module-level fixtures (no nesting under classes) to avoid `<locals>` in `__qualname__`.
- `tmp_path` + `monkeypatch.syspath_prepend` for synthetic packages in `test_discover.py`.
- `pytest.raises(SpecificError) as exc_info` + assertion on `exc_info.value.code` / `exc_info.value.details` for the error channel.
- `asyncio.run(...)` to drive coroutines (no `pytest-asyncio` required).

<div align="center">

## 🚦 Quality gates

</div>

```
uv run ruff format src/phronesis/tools tests/tools
uv run ruff check src/phronesis/tools tests/tools
uv run mypy src/phronesis/tools
uv run pytest tests/tools -q
```

All four must be green before commit. CI runs the same set against the whole repo.

`mypy` is configured in strict mode; every public symbol has explicit type annotations, and there are no `# type: ignore` comments outside three narrow places (Pydantic `create_model` dynamic kwargs, `Context` field re-assignment from `__post_init__`, and the `validated[self._context_param] = passthrough_context` cast where the optional `str` index needs narrowing).

<div align="center">

## 🛠️ Tech stack

</div>

| Library | Version | Used for |
|---|---|---|
| Python | `>= 3.11` | `Annotated`, `Self`, `asyncio.TimeoutError` alias, `StrEnum`. |
| Pydantic | `>= 2` | dynamic model creation (`create_model`), JSON-schema generation, validation. |
| `annotated_types` | latest | constraint markers for `Annotated`. |
| `httpx` | optional, lazy | only when `auto_map_exception` maps an `HTTPStatusError`. |
| stdlib | - | `inspect`, `functools`, `pkgutil`, `importlib`, `contextvars`, `threading`, `types.MappingProxyType`, `typing.get_type_hints`. |

<div align="center">

## 🔮 Future work

</div>

- **Strict OpenAI schema mode** (`strict: true` with full `additionalProperties: false` enforcement) - deferred until the provider stabilizes the contract.
- **More provider adapters** (Gemini, Bedrock, Cohere) - plug into `ProviderAdapter` Protocol; no `Tool` changes needed.
- **Per-effect runtime policies** - e.g. `EXPENSIVE` rate-limiting, `REQUIRES_CONFIRMATION` approval flow. Lives in a future `policy/` module; `tools/` only declares the tags.
- **Streaming tool outputs** - currently a single return value. Will require a new `invoke_stream` or generator-typed return on `Tool`.
- **`ToolSpec.output_schema`** - already a field on the spec but unused. A future iteration will derive it from the return annotation and surface it to providers that support output schemas.
- **`tool_id_generator` integration** - the singleton exists but is unused; future runtime may use it to mint anonymous tool ids for ad-hoc lambdas.
- **MCP integration** - the framework has an `mcp/` module placeholder. Tools will likely become the primary unit of export over MCP.
