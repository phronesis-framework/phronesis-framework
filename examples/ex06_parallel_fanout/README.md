<div align="center">
  <img src="../../public/assets/lockup/lockup-horizontal-dark.png" alt="ex06 - parallel_fanout" width="100%" />
</div>

<div align="center">

# ex06 - parallel_fanout

</div>

<div align="center">
  Fanout concurrente con `runtime.Parallel`: tres angulos del mismo input.
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

- `Parallel(nodes=(a, b, c))` ejecuta los N nodos a la vez.
- Mismo `input` a todos; output es `list` en orden de declaracion.
- Politica por defecto: `FailFastPolicy`.

<div align="center">

## 🚀 Development setup

</div>

```bash
CASSETTE_PATH=examples/ex06_parallel_fanout/cassette.jsonl \
  python -m examples.ex06_parallel_fanout.main
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
