<div align="center">
  <img src="../../public/assets/lockup/lockup-horizontal-dark.png" alt="ex01 - hello_agent" width="100%" />
</div>

<div align="center">

# ex01 - hello_agent

</div>

<div align="center">
  El "hola mundo" de Phronesis: un agente que suma dos números usando una tool.
</div>

<div align="center">
  <a href="../../src/">source</a> · <a href="../../tests/">tests</a> · <a href="../../docs/">docs</a> · <a href="../">examples</a>
</div>

<br />

<div align="center">
  <a href="https://go-skill-icons.vercel.app/">
    <img src="https://go-skill-icons.vercel.app/api/icons?i=python,typescript,react,nextjs,git&titles=true" alt="Technology stack" />
  </a>
</div>

---

<div align="center">

## 🎯 Purpose

</div>

- `@tool` sobre cuatro funciones sincronas (`add`, `sustract`, `times`, `divide`).
- `@agent` cableado con un provider, una system prompt y la tupla completa de tools.
- Tool-calling loop multi-paso: el modelo emite tres `tool_calls` encadenadas
  (add -> times -> sustract) y solo emite el texto final tras consumir todos
  los resultados intermedios.
- `Result.output` como `str` final.
- `max_iterations=8` para permitir varios turnos de tool calls en un mismo run.

<div align="center">

## 🚀 Development setup

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

## ✅ Expected output

</div>

```
(17 + 25) * 2 - 4 = 80.
```

(El texto exacto varia con el modelo; la cassette lo fija para que los tests sean
deterministas.)

<div align="center">

## 📚 Documentation

</div>

- [Example implementation](main.py)
- [Examples catalog](../README.md)
