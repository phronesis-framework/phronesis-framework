<div align="center">
  <img src="../../public/assets/lockup/lockup-horizontal-dark.png" alt="ex15 - handoff_chain" width="100%" />
</div>

<div align="center">

# ex15 - handoff_chain

</div>

<div align="center">
  `runtime.HandoffChain`: triage delega a billing/tech segun marker textual.
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

- `HandoffChain(agents=mapping, initial=name, handoff_extractor=fn)`.
- Cada agente decide a quien pasar el turno; output sin marker termina la cadena.
- Custom `handoff_extractor` parsea `[handoff:NAME]` del texto.

<div align="center">

## 🚀 Development setup

</div>

```bash
CASSETTE_PATH=examples/ex15_handoff_chain/cassette.jsonl \
  python -m examples.ex15_handoff_chain.main
```

<div align="center">

## ✅ Expected output

</div>

The example prints its execution result. The exact output depends on the selected provider and input; see [`main.py`](main.py) for the result handling.

<div align="center">

## 📚 Documentation

</div>

- [Example implementation](main.py)
- [Examples catalog](../README.md)
