<div align="center">
  <img src="../../public/assets/lockup/lockup-horizontal-dark.png" alt="ex02 - research_assistant" width="100%" />
</div>

<div align="center">

# ex02 - research_assistant

</div>

<div align="center">
  Un agente que encadena tres tools (search -> fetch_url -> summarize) para responder a una pregunta.
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

- Multi-tool loop: la system prompt obliga al modelo a llamar tres tools
  en orden.
- Dependencias entre llamadas: el argumento de `fetch_url` viene de un
  resultado de `search`, y el argumento de `summarize` viene del cuerpo
  devuelto por `fetch_url`.
- `max_iterations` para permitir mas de un tool call por run.

<div align="center">

## 🚀 Development setup

</div>

```bash
# Contra Ollama
python -m examples.ex02_research_assistant.main

# Contra cassette (sin red)
CASSETTE_PATH=examples/ex02_research_assistant/cassette.jsonl \
  python -m examples.ex02_research_assistant.main
```

<div align="center">

## ✅ Expected output

</div>

```
Phronesis is a Python 3.11+ framework that gives developers the primitives to build production-grade agents.
```

Los tools (`search`, `fetch_url`, `summarize`) son **stubs** que devuelven
contenido fijo: el ejemplo se centra en el patron de encadenamiento, no en
acceso a red real.

<div align="center">

## 📚 Documentation

</div>

- [Example implementation](main.py)
- [Examples catalog](../README.md)
