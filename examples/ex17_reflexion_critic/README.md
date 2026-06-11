#

<div align="center">

# ex17 - reflexion_critic

</div>

<div align="center">
  `runtime.Reflexion`: actor + critic; reintenta hasta que el critic acepta.
</div>

---

## Que demuestra

- `Reflexion(actor=..., critic=fn, max_iterations=N)`.
- `critic` devuelve `ValidationResult(valid, feedback)`.
- Si `valid=False`, el actor reintenta usando el feedback.

## Como correr

```bash
CASSETTE_PATH=examples/ex17_reflexion_critic/cassette.jsonl \
  python -m examples.ex17_reflexion_critic.main
```
