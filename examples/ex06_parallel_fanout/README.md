#

<div align="center">

# ex06 - parallel_fanout

</div>

<div align="center">
  Fanout concurrente con `runtime.Parallel`: tres angulos del mismo input.
</div>

---

## Que demuestra

- `Parallel(nodes=(a, b, c))` ejecuta los N nodos a la vez.
- Mismo `input` a todos; output es `list` en orden de declaracion.
- Politica por defecto: `FailFastPolicy`.

## Como correr

```bash
CASSETTE_PATH=examples/ex06_parallel_fanout/cassette.jsonl \
  python -m examples.ex06_parallel_fanout.main
```
