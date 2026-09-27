<div align="center">
  <img src="../../public/assets/lockup/lockup-horizontal-dark.png" alt="ex19 - plan_and_execute" width="100%" />
</div>

<div align="center">

# ex19 - plan_and_execute

</div>

<div align="center">
  `runtime.PlanAndExecute`: planner emite pasos; executor los ejecuta en orden.
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

- `PlanAndExecute(planner=..., executor=..., step_extractor=fn)`.
- `step_extractor` parsea la salida del planner; aqui split por lineas.
- `outcome.output` es una lista con el resultado de cada step.

<div align="center">

## 🚀 Development setup

</div>

```bash
CASSETTE_PATH=examples/ex19_plan_and_execute/cassette.jsonl \
  python -m examples.ex19_plan_and_execute.main
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
