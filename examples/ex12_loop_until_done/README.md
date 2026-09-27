<div align="center">
  <img src="../../public/assets/lockup/lockup-horizontal-dark.png" alt="ex12 - loop_until_done" width="100%" />
</div>

<div align="center">

# ex12 - loop_until_done

</div>

<div align="center">
  `runtime.Loop`: itera el body hasta que `until(output)` es True.
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

- `Loop(body=..., until=fn, max_iterations=N)` reinyecta output como input.
- `until(output)` se evalua tras cada turno; corta cuando es True.
- `max_iterations` evita bucles infinitos (`LoopExhaustedError`).

<div align="center">

## 🚀 Development setup

</div>

```bash
python -m examples.ex12_loop_until_done.main
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
