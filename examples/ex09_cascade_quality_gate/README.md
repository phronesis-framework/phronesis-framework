#

<div align="center">

# ex09 - cascade_quality_gate

</div>

<div align="center">
  `runtime.Cascade`: prueba modelos baratos; escala si la respuesta es corta.
</div>

---

## Que demuestra

- `Cascade(nodes=..., acceptance=fn)` itera hasta que `fn(output)` es `True`.
- Primer nodo rechazado -> probar el siguiente; el primero aceptado gana.
- `acceptance` es callable sincrona o async.

## Como correr

```bash
CASSETTE_PATH=examples/ex09_cascade_quality_gate/cassette.jsonl \
  python -m examples.ex09_cascade_quality_gate.main
```
