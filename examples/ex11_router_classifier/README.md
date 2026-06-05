#

<div align="center">

# ex11 - router_classifier

</div>

<div align="center">
  `runtime.Router`: classifier por keywords elige una de tres voces.
</div>

---

## Que demuestra

- `Router(classifier=fn, routes=mapping, default=...)` dispatcheo por clave.
- `fn(input)` devuelve la clave; el `routes[key]` se ejecuta.
- `default` cubre claves no mapeadas.

## Como correr

```bash
CASSETTE_PATH=examples/ex11_router_classifier/cassette.jsonl \
  python -m examples.ex11_router_classifier.main
```
