#

<div align="center">

# ex20 - tree_search_beam

</div>

<div align="center">
  `runtime.TreeSearch`: expander + evaluator + beam search.
</div>

---

## Que demuestra

- `TreeSearch(expander=..., evaluator=..., max_depth=N, beam_width=K)`.
- `expander(node)` produce hijos; `evaluator(cand)` devuelve un score numerico.
- Mantiene los top-K en cada nivel; gana la mejor hoja al alcanzar `max_depth`.

## Como correr

```bash
python -m examples.ex20_tree_search_beam.main
```
