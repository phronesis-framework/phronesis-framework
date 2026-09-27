<div align="center">
  <img src="../../public/assets/lockup/lockup-horizontal-dark.png" alt="ex20 - tree_search_beam" width="100%" />
</div>

<div align="center">

# ex20 - tree_search_beam

</div>

<div align="center">
  `runtime.TreeSearch`: expander + evaluator + beam search.
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

- `TreeSearch(expander=..., evaluator=..., max_depth=N, beam_width=K)`.
- `expander(node)` produce hijos; `evaluator(cand)` devuelve un score numerico.
- Mantiene los top-K en cada nivel; gana la mejor hoja al alcanzar `max_depth`.

<div align="center">

## 🚀 Development setup

</div>

```bash
python -m examples.ex20_tree_search_beam.main
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
