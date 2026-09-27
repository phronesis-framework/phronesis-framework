<div align="center">
  <img src="../../public/assets/lockup/lockup-horizontal-dark.png" alt="ex04 - bull_vs_bear_debate" width="100%" />
</div>

<div align="center">

# ex04 - bull_vs_bear_debate

</div>

<div align="center">
  Dos agentes (bull y bear) debaten durante dos rondas; un tercero modera y emite veredicto.
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

- `runtime.Debate` orquesta N rondas sobre una tupla de participantes.
- `agent_node(agent)` adapta un `Agent` para que satisfaga el protocolo
  `Executable` que espera el runtime.
- `ExecutionContext.new()` crea el contexto raiz desde el que se invoca el modo.
- El moderador se ejecuta una sola vez al final y su salida es la salida del
  `RunOutcome`.
- Los tres agentes (bull, bear, moderator) **comparten un mismo provider**;
  cuando se corre contra cassette esto significa que las 5 respuestas (2 rondas
  x 2 participantes + 1 moderador) viven en un unico fichero JSONL.

<div align="center">

## 🚀 Development setup

</div>

```bash
# Contra Ollama
python -m examples.ex04_bull_vs_bear_debate.main

# Contra cassette (sin red)
CASSETTE_PATH=examples/ex04_bull_vs_bear_debate/cassette.jsonl \
  python -m examples.ex04_bull_vs_bear_debate.main
```

<div align="center">

## ✅ Expected output

</div>

Un parrafo con el veredicto del moderador. Con la cassette:

```
The bull case rests on productivity-per-hour and retention gains observed in pilots;
the bear case warns about service gaps, redistributed workload and novelty effects.
...
Verdict: cautiously pro four-day week for knowledge work...
```

<div align="center">

## 📚 Documentation

</div>

- [Example implementation](main.py)
- [Examples catalog](../README.md)
