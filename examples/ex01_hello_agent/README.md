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

- `@tool` sobre una funcion sincrona.
- `@agent` cableado con un provider, una system prompt y un set de tools.
- Tool-calling loop completo: primera respuesta del modelo emite `tool_calls`,
  el framework ejecuta la tool, y la segunda respuesta del modelo produce el
  texto final.
- `Result.output` como `str` final.

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
17 + 25 = 42.
```

(El texto exacto varia con el modelo; la cassette lo fija para que los tests sean
deterministas.)
