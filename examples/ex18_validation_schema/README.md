<div align="center">
  <img src="../../public/assets/lockup/lockup-horizontal-dark.png" alt="ex18 - validation_schema" width="100%" />
</div>

<div align="center">

# ex18 - validation_schema

</div>

<div align="center">
  `runtime.Validation`: reintenta hasta que el validator acepte el JSON.
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

- `Validation(node=..., validator=fn, max_attempts=N)`.
- `validator` devuelve `ValidationResult`; el feedback se inyecta al reintentar.
- Util para forzar structured output sin features especificas del provider.

<div align="center">

## 🚀 Development setup

</div>

```bash
CASSETTE_PATH=examples/ex18_validation_schema/cassette.jsonl \
  python -m examples.ex18_validation_schema.main
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
