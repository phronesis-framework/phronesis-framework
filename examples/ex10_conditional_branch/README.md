<div align="center">
  <img src="../../public/assets/lockup/lockup-horizontal-dark.png" alt="ex10 - conditional_branch" width="100%" />
</div>

<div align="center">

# ex10 - conditional_branch

</div>

<div align="center">
  `runtime.Conditional`: predicate decide entre dos agents.
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

- `Conditional(predicate=fn, on_true=a, on_false=b)` ejecuta una de las dos ramas.
- `fn` puede ser sync o async; recibe el `input`.
- Solo se ejecuta el branch elegido, el otro nunca llama al modelo.

<div align="center">

## 🚀 Development setup

</div>

```bash
CASSETTE_PATH=examples/ex10_conditional_branch/cassette.jsonl \
  python -m examples.ex10_conditional_branch.main
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
