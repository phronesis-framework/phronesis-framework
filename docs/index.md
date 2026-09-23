#

<div align="center">
  <img src="../public/assets/lockup/lockup-horizontal-dark.svg" alt="Phronesis Framework" width="60%" />
</div>

<div align="center">

# Phronesis Framework - Documentation

</div>

<div align="center">
  Root documentation index. Mirrors the structure of <code>src/phronesis/</code>.
</div>

<div align="center">
  <a href="https://github.com/phronesis-framework/phronesis">repo</a> ·
  <a href="../LICENSE">license</a>
</div>

<div align="center">
  <img src="https://skillicons.dev/icons?i=py,docker,grafana,prometheus,githubactions" alt="Tech stack" />
</div>

---

<div align="center">

## 🗺️ Map

</div>

| Area | Status | Documentation |
|---|---|---|
| `_internal` - shared infrastructure | in progress | [internal/](./internal/index.md) |
| `tools` - tool declaration and registry | stable | [tools/](./tools/index.md) |
| `agents` - `@agent`, runtime, sessions, tool-calling loop | stable | [agents/](./agents/index.md) |
| `runtime` - agent orchestration (19 modes) | stable | [runtime/](./runtime/index.md) |
| `providers` - per-LLM-vendor adapters | stable | [providers/](./providers/index.md) |
| `obs` - observability (spans, metrics, log correlation) | stable | [obs/](./obs/index.md) |
| `context` - ContextBuilder + Context injected into tools | stable | [context/](./context/index.md) |
| `memory` - working/kv/vector/episodic stores + checkpoints | stable | [memory/](./memory/index.md) |
| `pipelines` - declarative composition of named Executables | stable | [pipelines/](./pipelines/index.md) |
| `mcp` - Model Context Protocol client and server | stable | [mcp/](./mcp/index.md) |
| `middleware` - onion chain over `LLMProvider.complete` | stable | [middleware/](./middleware/index.md) |
| `replay` - record/replay of LLM responses in JSONL cassettes | stable | [replay/](./replay/index.md) |
| `core` - domain types (`Message`, `ContentBlock`) | stable | [core/](./core/index.md) |
| `communication` - session identity (`SessionId`) | stable | [communication/](./communication/index.md) |

<div align="center">

## 📐 Decisions and plans

</div>
