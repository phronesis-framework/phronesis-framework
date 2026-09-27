<div align="center">
  <img src="../../public/assets/lockup/lockup-horizontal-dark.png" alt="ex21 - map_reduce_summarize" width="100%" />
</div>

<div align="center">

# ex21 - map_reduce_summarize

</div>

<div align="center">
  `runtime.MapReduce`: split -> mapper paralelo -> reducer.
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

- `MapReduce(splitter=fn, mapper=node, reducer=fn)`.
- `splitter(input)` produce items; `mapper` se invoca uno por item en paralelo.
- `reducer(outputs)` agrega los resultados en el output final.

<div align="center">

## 🚀 Development setup

</div>

```bash
CASSETTE_PATH=examples/ex21_map_reduce_summarize/cassette.jsonl \
  python -m examples.ex21_map_reduce_summarize.main
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
