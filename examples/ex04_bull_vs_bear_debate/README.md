#

<div align="center">

# ex04 - bull_vs_bear_debate

</div>

<div align="center">
  Dos agentes (bull y bear) debaten durante dos rondas; un tercero modera y emite veredicto.
</div>

<div align="center">
  <a href="../README.md">examples</a> ·
  <a href="../../src/phronesis/">source</a>
</div>

---

<div align="center">

## Que demuestra

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

## Como correr

</div>

```bash
# Contra Ollama
python -m examples.ex04_bull_vs_bear_debate.main

# Contra cassette (sin red)
CASSETTE_PATH=examples/ex04_bull_vs_bear_debate/cassette.jsonl \
  python -m examples.ex04_bull_vs_bear_debate.main
```

<div align="center">

## Que esperar

</div>

Un parrafo con el veredicto del moderador. Con la cassette:

```
The bull case rests on productivity-per-hour and retention gains observed in pilots;
the bear case warns about service gaps, redistributed workload and novelty effects.
...
Verdict: cautiously pro four-day week for knowledge work...
```
