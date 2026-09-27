<div align="center">
  <img src="../../public/assets/lockup/lockup-horizontal-dark.png" alt="ex07 - race_fastest_wins" width="100%" />
</div>

<div align="center">

# ex07 - race_fastest_wins

</div>

<div align="center">
  `runtime.Race`: cache rapida vs upstream lento. Gana el primero.
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

- `Race(nodes=...)` corre los nodos en paralelo y devuelve el primero.
- Cancela los demas en cuanto hay ganador.
- `callable_node(async_fn)` envuelve coroutines en `Executable`.

<div align="center">

## 🚀 Development setup

</div>

```bash
python -m examples.ex07_race_fastest_wins.main
```

Sin cassette: los dos nodos son funciones puras-Python, deterministicas.

<div align="center">

## ✅ Expected output

</div>

The example prints its execution result. The exact output depends on the selected provider and input; see [`main.py`](main.py) for the result handling.

<div align="center">

## 📚 Documentation

</div>

- [Example implementation](main.py)
- [Examples catalog](../README.md)
