<div align="center">
  <img src="../../public/assets/lockup/lockup-horizontal-dark.png" alt="ex08 - fallback_chain" width="100%" />
</div>

<div align="center">

# ex08 - fallback_chain

</div>

<div align="center">
  `runtime.Fallback`: primario falla, cache degradada cubre.
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

- `Fallback(primary=..., fallbacks=(...,))` cae al siguiente si el actual lanza.
- Sirve para degradar (cache, mirror, mock) sin propagar el error.

<div align="center">

## 🚀 Development setup

</div>

```bash
python -m examples.ex08_fallback_chain.main
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
