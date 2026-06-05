#

<div align="center">

# ex16 - supervisor_dispatch

</div>

<div align="center">
  `runtime.Supervisor`: dispatcher delega a workers hasta que termina.
</div>

---

## Que demuestra

- `Supervisor(dispatcher=..., workers=mapping, route_extractor=fn)`.
- Dispatcher se invoca cada iteracion; si emite ruta, ejecuta worker.
- Sin ruta -> termina. `max_iterations` corta loops infinitos.

## Como correr

```bash
CASSETTE_PATH=examples/ex16_supervisor_dispatch/cassette.jsonl \
  python -m examples.ex16_supervisor_dispatch.main
```
