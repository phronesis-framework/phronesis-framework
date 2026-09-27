<div align="center">
  <img src="../../public/assets/lockup/lockup-horizontal-dark.png" alt="ex13 - retry_with_backoff" width="100%" />
</div>

<div align="center">

# ex13 - retry_with_backoff

</div>

<div align="center">
  `runtime.Retry`: reintenta con backoff exponencial hasta exito o tope.
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

- `Retry(node=..., max_attempts=N, on=(Exc,...))` filtra que excepciones reintentar.
- `backoff_initial_s` * `backoff_multiplier^attempt`, capado por `backoff_max_s`.
- Si se agotan los reintentos, propaga la ultima excepcion.

<div align="center">

## 🚀 Development setup

</div>

```bash
python -m examples.ex13_retry_with_backoff.main
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
