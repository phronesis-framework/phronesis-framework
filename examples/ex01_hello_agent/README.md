#

<div align="center">

# ex01 - hello_agent

</div>

<div align="center">
  El "hola mundo" de Phronesis: un agente que suma dos números usando una tool.
</div>

<div align="center">
  <a href="../README.md">examples</a> ·
  <a href="../../src/phronesis/">source</a>
</div>

---

<div align="center">

## Que demuestra

</div>

- `@tool` sobre cuatro funciones sincronas (`add`, `sustract`, `times`, `divide`).
- `@agent` cableado con un provider, una system prompt y la tupla completa de tools.
- Tool-calling loop multi-paso: el modelo emite tres `tool_calls` encadenadas
  (add -> times -> sustract) y solo emite el texto final tras consumir todos
  los resultados intermedios.
- `Result.output` como `str` final.
- `max_iterations=8` para permitir varios turnos de tool calls en un mismo run.

<div align="center">

## Como correr

</div>

Contra Ollama local (necesita `ollama pull qwen2.5:3b`):

```bash
python -m examples.ex01_hello_agent.main
```

Contra la cassette grabada (sin red, determinista):

```bash
CASSETTE_PATH=examples/ex01_hello_agent/cassette.jsonl \
  python -m examples.ex01_hello_agent.main
```

<div align="center">

## Que esperar

</div>

```
(17 + 25) * 2 - 4 = 80.
```

(El texto exacto varia con el modelo; la cassette lo fija para que los tests sean
deterministas.)
