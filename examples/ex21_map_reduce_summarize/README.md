#

<div align="center">

# ex21 - map_reduce_summarize

</div>

<div align="center">
  `runtime.MapReduce`: split -> mapper paralelo -> reducer.
</div>

---

## Que demuestra

- `MapReduce(splitter=fn, mapper=node, reducer=fn)`.
- `splitter(input)` produce items; `mapper` se invoca uno por item en paralelo.
- `reducer(outputs)` agrega los resultados en el output final.

## Como correr

```bash
CASSETTE_PATH=examples/ex21_map_reduce_summarize/cassette.jsonl \
  python -m examples.ex21_map_reduce_summarize.main
```
