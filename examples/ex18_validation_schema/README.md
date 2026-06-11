#

<div align="center">

# ex18 - validation_schema

</div>

<div align="center">
  `runtime.Validation`: reintenta hasta que el validator acepte el JSON.
</div>

---

## Que demuestra

- `Validation(node=..., validator=fn, max_attempts=N)`.
- `validator` devuelve `ValidationResult`; el feedback se inyecta al reintentar.
- Util para forzar structured output sin features especificas del provider.

## Como correr

```bash
CASSETTE_PATH=examples/ex18_validation_schema/cassette.jsonl \
  python -m examples.ex18_validation_schema.main
```
