<div align="center">
  <img src="../../public/assets/lockup/lockup-horizontal-dark.png" alt="ex11 - router_classifier" width="100%" />
</div>

<div align="center">

# ex11 - router_classifier

</div>

<div align="center">
  `runtime.Router`: classifier por keywords elige una de tres voces.
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

- `Router(classifier=fn, routes=mapping, default=...)` dispatcheo por clave.
- `fn(input)` devuelve la clave; el `routes[key]` se ejecuta.
- `default` cubre claves no mapeadas.

<div align="center">

## 🚀 Development setup

</div>

```bash
CASSETTE_PATH=examples/ex11_router_classifier/cassette.jsonl \
  python -m examples.ex11_router_classifier.main
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
