<div align="center">
  <img src="../../public/assets/lockup/lockup-horizontal-dark.png" alt="ex03 - chat_with_memory" width="100%" />
</div>

<div align="center">

# ex03 - chat_with_memory

</div>

<div align="center">
  Conversacion multi-turno usando agent.session(): el agente recuerda lo que el usuario dijo antes.
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

- `agent.session()` crea una `Session` con su propio `SessionId`.
- Cada `session.run(message)` reutiliza el historial acumulado:
  `system` + `user` + `assistant` se concatenan turno a turno.
- En el segundo turno, cuando el usuario pregunta "what's my name?",
  el modelo ya tiene en su contexto que el usuario se presento como
  "Eduardo" en el primer turno.

<div align="center">

## 🚀 Development setup

</div>

```bash
# Contra Ollama
python -m examples.ex03_chat_with_memory.main

# Contra cassette (sin red)
CASSETTE_PATH=examples/ex03_chat_with_memory/cassette.jsonl \
  python -m examples.ex03_chat_with_memory.main
```

<div align="center">

## ✅ Expected output

</div>

```
> Hi, my name is Eduardo.
< Hi Eduardo, nice to meet you. How can I help today?

> Quick check: what's my name?
< Your name is Eduardo.
```

<div align="center">

## 🔹 Notes

</div>

`Session` mantiene el historial **en memoria del proceso**. Persistencia a
disco (KV / vector / archivo) se cubre en ejemplos posteriores del catalogo.

<div align="center">

## 📚 Documentation

</div>

- [Example implementation](main.py)
- [Examples catalog](../README.md)
