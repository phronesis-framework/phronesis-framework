#

<div align="center">

# ex13 - retry_with_backoff

</div>

<div align="center">
  `runtime.Retry`: reintenta con backoff exponencial hasta exito o tope.
</div>

---

## Que demuestra

- `Retry(node=..., max_attempts=N, on=(Exc,...))` filtra que excepciones reintentar.
- `backoff_initial_s` * `backoff_multiplier^attempt`, capado por `backoff_max_s`.
- Si se agotan los reintentos, propaga la ultima excepcion.

## Como correr

```bash
python -m examples.ex13_retry_with_backoff.main
```
