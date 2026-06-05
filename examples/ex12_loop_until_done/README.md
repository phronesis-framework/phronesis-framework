#

<div align="center">

# ex12 - loop_until_done

</div>

<div align="center">
  `runtime.Loop`: itera el body hasta que `until(output)` es True.
</div>

---

## Que demuestra

- `Loop(body=..., until=fn, max_iterations=N)` reinyecta output como input.
- `until(output)` se evalua tras cada turno; corta cuando es True.
- `max_iterations` evita bucles infinitos (`LoopExhaustedError`).

## Como correr

```bash
python -m examples.ex12_loop_until_done.main
```
