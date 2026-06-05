#

<div align="center">

# ex22 - approval_gate

</div>

<div align="center">
  `runtime.Approval`: ejecuta un nodo y deja que un callback acepte o rechace el output.
</div>

---

## Que demuestra

- `Approval(node=..., approve=fn, timeout_s=...)`.
- `approve` puede ser sync o async; recibe el output del nodo y devuelve `bool`.
- Si el callback devuelve falso o agota el timeout, el `RunOutcome` falla con `ApprovalDeniedError` / `ApprovalTimeoutError`.

## Como correr

```bash
CASSETTE_PATH=examples/ex22_approval_gate/cassette.jsonl \
  python -m examples.ex22_approval_gate.main
```
