<div align="center">
  <img src="../../public/assets/lockup/lockup-horizontal-dark.png" alt="ex17 - reflexion_critic" width="100%" />
</div>

<div align="center">

# ex17 - reflexion_critic

</div>

<div align="center">
  `runtime.Reflexion`: actor + critic; reintenta hasta que el critic acepta.
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

- `Reflexion(actor=..., critic=fn, max_iterations=N)`.
- `critic` devuelve `ValidationResult(valid, feedback)`.
- Si `valid=False`, el actor reintenta usando el feedback.

<div align="center">

## 🚀 Development setup

</div>

```bash
CASSETTE_PATH=examples/ex17_reflexion_critic/cassette.jsonl \
  python -m examples.ex17_reflexion_critic.main
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
