#

<div align="center">

# ex15 - handoff_chain

</div>

<div align="center">
  `runtime.HandoffChain`: triage delega a billing/tech segun marker textual.
</div>

---

## Que demuestra

- `HandoffChain(agents=mapping, initial=name, handoff_extractor=fn)`.
- Cada agente decide a quien pasar el turno; output sin marker termina la cadena.
- Custom `handoff_extractor` parsea `[handoff:NAME]` del texto.

## Como correr

```bash
CASSETTE_PATH=examples/ex15_handoff_chain/cassette.jsonl \
  python -m examples.ex15_handoff_chain.main
```
