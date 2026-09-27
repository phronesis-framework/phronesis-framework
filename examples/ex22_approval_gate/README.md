<div align="center">
  <img src="../../public/assets/lockup/lockup-horizontal-dark.png" alt="ex22 - approval_gate" width="100%" />
</div>

<div align="center">

# ex22 - approval_gate

</div>

<div align="center">
  `runtime.Approval`: ejecuta un nodo y deja que un callback acepte o rechace el output.
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

- `Approval(node=..., approve=fn, timeout_s=...)`.
- `approve` puede ser sync o async; recibe el output del nodo y devuelve `bool`.
- Si el callback devuelve falso o agota el timeout, el `RunOutcome` falla con `ApprovalDeniedError` / `ApprovalTimeoutError`.

<div align="center">

## 🚀 Development setup

</div>

```bash
CASSETTE_PATH=examples/ex22_approval_gate/cassette.jsonl \
  python -m examples.ex22_approval_gate.main
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
