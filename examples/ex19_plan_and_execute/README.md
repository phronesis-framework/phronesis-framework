#

<div align="center">

# ex19 - plan_and_execute

</div>

<div align="center">
  `runtime.PlanAndExecute`: planner emite pasos; executor los ejecuta en orden.
</div>

---

## Que demuestra

- `PlanAndExecute(planner=..., executor=..., step_extractor=fn)`.
- `step_extractor` parsea la salida del planner; aqui split por lineas.
- `outcome.output` es una lista con el resultado de cada step.

## Como correr

```bash
CASSETTE_PATH=examples/ex19_plan_and_execute/cassette.jsonl \
  python -m examples.ex19_plan_and_execute.main
```
