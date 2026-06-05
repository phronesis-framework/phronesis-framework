#

<div align="center">

# Phronesis Framework - examples

</div>

<div align="center">
  Catalogo de mini-sistemas que ejercitan las primitivas de Phronesis. Cada ejemplo es ejecutable, documentado y testeado contra una cassette grabada.
</div>

<div align="center">
  <a href="../docs/index.md">docs</a> ·
  <a href="../src/phronesis/">source</a> ·
  <a href="../tests/examples/">tests</a>
</div>

---

<div align="center">

## Catalogo

</div>

### Fundamentos

| #  | Ejemplo                                                       | Demuestra                                  |
| -- | ------------------------------------------------------------- | ------------------------------------------ |
| 01 | [`ex01_hello_agent`](./ex01_hello_agent/)                     | `@agent`, `@tool`, tool-calling loop       |
| 02 | [`ex02_research_assistant`](./ex02_research_assistant/)       | multi-tool loop, dependencias entre tools  |
| 03 | [`ex03_chat_with_memory`](./ex03_chat_with_memory/)           | `Session`, historial multi-turno           |
| 04 | [`ex04_bull_vs_bear_debate`](./ex04_bull_vs_bear_debate/)     | `runtime.Debate`, moderador                |

### Runtime modes - primitivas

| #  | Ejemplo                                                       | Demuestra                                  |
| -- | ------------------------------------------------------------- | ------------------------------------------ |
| 05 | [`ex05_sequence_pipeline`](./ex05_sequence_pipeline/)         | `runtime.Sequence` (researcher->writer->editor) |
| 06 | [`ex06_parallel_fanout`](./ex06_parallel_fanout/)             | `runtime.Parallel` (3 perspectivas)        |
| 07 | [`ex07_race_fastest_wins`](./ex07_race_fastest_wins/)         | `runtime.Race` (primer ganador cancela el resto) |
| 08 | [`ex08_fallback_chain`](./ex08_fallback_chain/)               | `runtime.Fallback` (cae al siguiente si falla) |
| 09 | [`ex09_cascade_quality_gate`](./ex09_cascade_quality_gate/)   | `runtime.Cascade` (acepta o escala)        |

### Runtime modes - control flow

| #  | Ejemplo                                                       | Demuestra                                  |
| -- | ------------------------------------------------------------- | ------------------------------------------ |
| 10 | [`ex10_conditional_branch`](./ex10_conditional_branch/)       | `runtime.Conditional` (predicate -> rama)  |
| 11 | [`ex11_router_classifier`](./ex11_router_classifier/)         | `runtime.Router` (clave -> destino)        |
| 12 | [`ex12_loop_until_done`](./ex12_loop_until_done/)             | `runtime.Loop` (re-itera mientras truthy)  |
| 13 | [`ex13_retry_with_backoff`](./ex13_retry_with_backoff/)       | `runtime.Retry` (reintentos con backoff)   |

### Runtime modes - multi-agente

| #  | Ejemplo                                                       | Demuestra                                  |
| -- | ------------------------------------------------------------- | ------------------------------------------ |
| 14 | [`ex14_consensus_vote`](./ex14_consensus_vote/)               | `runtime.Consensus` (voto mayoritario)     |
| 15 | [`ex15_handoff_chain`](./ex15_handoff_chain/)                 | `runtime.HandoffChain` (delegacion explicita) |
| 16 | [`ex16_supervisor_dispatch`](./ex16_supervisor_dispatch/)     | `runtime.Supervisor` (dispatcher + workers)|

### Runtime modes - cognitivos

| #  | Ejemplo                                                       | Demuestra                                  |
| -- | ------------------------------------------------------------- | ------------------------------------------ |
| 17 | [`ex17_reflexion_critic`](./ex17_reflexion_critic/)           | `runtime.Reflexion` (actor + critic)       |
| 18 | [`ex18_validation_schema`](./ex18_validation_schema/)         | `runtime.Validation` (re-prompt hasta valido)|
| 19 | [`ex19_plan_and_execute`](./ex19_plan_and_execute/)           | `runtime.PlanAndExecute` (planner + executor)|
| 20 | [`ex20_tree_search_beam`](./ex20_tree_search_beam/)           | `runtime.TreeSearch` (expander + evaluator)|
| 21 | [`ex21_map_reduce_summarize`](./ex21_map_reduce_summarize/)   | `runtime.MapReduce` (split/map/reduce)     |
| 22 | [`ex22_approval_gate`](./ex22_approval_gate/)                 | `runtime.Approval` (gate humano/automatico)|

Todos corren con `CASSETTE_PATH=examples/exNN_xxx/cassette.jsonl python -m examples.exNN_xxx.main` o contra Ollama si no se define la variable.

<div align="center">

## Como correr

</div>

### Contra cassette (determinista, sin red)

Cada ejemplo trae una cassette JSONL preparada. Solo hay que apuntar
`CASSETTE_PATH` al fichero:

```bash
CASSETTE_PATH=examples/ex01_hello_agent/cassette.jsonl \
  python -m examples.ex01_hello_agent.main
```

Los smoke tests en `tests/examples/` corren todos los ejemplos de esta
manera, asi que la suite global (`uv run pytest -q`) no necesita Ollama
ni acceso a red.

### Contra Ollama local

Levanta Ollama y descarga el modelo:

```bash
ollama pull qwen2.5:3b
python -m examples.ex01_hello_agent.main
```

Variables de entorno opcionales:

- `OLLAMA_MODEL` (default `qwen2.5:3b`)
- `OLLAMA_HOST` (default `http://localhost:11434`)

<div align="center">

## Como regrabar cassettes

</div>

Si cambias el codigo de un ejemplo (prompt, tools, numero de rondas, etc.)
la cassette comiteada queda obsoleta. Para regrabar contra Ollama:

```bash
ollama pull qwen2.5:3b

RECORD_CASSETTE=examples/ex01_hello_agent/cassette.jsonl \
  python -m examples.ex01_hello_agent.main
```

`RECORD_CASSETTE` instruye al helper `examples/_shared/provider.py` a
envolver el provider Ollama real con `RecordingProvider`, que escribe
cada respuesta al fichero indicado en formato JSONL.

> **Precedencia**: si `CASSETTE_PATH` esta definido, se ignora `RECORD_CASSETTE`.

<div align="center">

## Estructura

</div>

```
examples/
├── README.md                          este indice
├── _shared/
│   └── provider.py                    build_provider() helper compartido
├── ex01_hello_agent/
│   ├── main.py                        entry point
│   ├── cassette.jsonl                 grabacion JSONL
│   └── README.md                      que demuestra y como correr
├── ex02_research_assistant/
│   ├── main.py
│   ├── tools.py                       stubs de search/fetch/summarize
│   ├── cassette.jsonl
│   └── README.md
├── ex03_chat_with_memory/
│   ├── main.py
│   ├── cassette.jsonl
│   └── README.md
└── ex04_bull_vs_bear_debate/
    ├── main.py
    ├── prompts.py                     SYSTEM_BULL / BEAR / MODERATOR
    ├── cassette.jsonl
    └── README.md
```

<div align="center">

## Proximos lotes

</div>

- **MCP**: cliente y servidor MCP.
- **Memoria avanzada**: vector RAG, checkpoint/resume.
- **Middleware**: logging, tracing, rate limiting.
- **Structured output**: validacion Pydantic + retry semantico.
