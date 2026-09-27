<div align="center">
  <img src="../../public/assets/lockup/lockup-horizontal-dark.png" alt="ex16 - supervisor_dispatch" width="100%" />
</div>

<div align="center">

# ex16 - supervisor_dispatch

</div>

<div align="center">
  `runtime.Supervisor`: dispatcher delega a workers hasta que termina.
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

- `Supervisor(dispatcher=..., workers=mapping, route_extractor=fn)`.
- Dispatcher se invoca cada iteracion; si emite ruta, ejecuta worker.
- Sin ruta -> termina. `max_iterations` corta loops infinitos.

<div align="center">

## 🚀 Development setup

</div>

```bash
CASSETTE_PATH=examples/ex16_supervisor_dispatch/cassette.jsonl \
  python -m examples.ex16_supervisor_dispatch.main
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
