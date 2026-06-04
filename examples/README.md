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

| #  | Ejemplo                                                       | Demuestra                                | Provider          | Como correr                                              |
| -- | ------------------------------------------------------------- | ---------------------------------------- | ----------------- | -------------------------------------------------------- |
| 01 | [`ex01_hello_agent`](./ex01_hello_agent/)                     | `@agent`, `@tool`, tool-calling loop     | Ollama / Cassette | `python -m examples.ex01_hello_agent.main`               |
| 02 | [`ex02_research_assistant`](./ex02_research_assistant/)       | multi-tool loop, dependencias entre tools| Ollama / Cassette | `python -m examples.ex02_research_assistant.main`        |
| 03 | [`ex03_chat_with_memory`](./ex03_chat_with_memory/)           | `Session`, historial multi-turno         | Ollama / Cassette | `python -m examples.ex03_chat_with_memory.main`          |
| 04 | [`ex04_bull_vs_bear_debate`](./ex04_bull_vs_bear_debate/)     | `runtime.Debate`, `agent_node`, moderador| Ollama / Cassette | `python -m examples.ex04_bull_vs_bear_debate.main`       |

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

Los smoke tests en `tests/examples/` corren los cuatro ejemplos de esta
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

## Proximos lotes (no en M1)

</div>

- **M2**: pipeline secuencial, parallel fanout, structured output con Pydantic.
- **M3**: supervisor, handoff chain, router condicional.
- **M4**: cliente MCP, servidor MCP.
- **M5**: middleware logging, checkpoint/resume, vector RAG.
