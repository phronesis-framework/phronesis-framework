#

<div align="center">

# ex10 - conditional_branch

</div>

<div align="center">
  `runtime.Conditional`: predicate decide entre dos agents.
</div>

---

## Que demuestra

- `Conditional(predicate=fn, on_true=a, on_false=b)` ejecuta una de las dos ramas.
- `fn` puede ser sync o async; recibe el `input`.
- Solo se ejecuta el branch elegido, el otro nunca llama al modelo.

## Como correr

```bash
CASSETTE_PATH=examples/ex10_conditional_branch/cassette.jsonl \
  python -m examples.ex10_conditional_branch.main
```
