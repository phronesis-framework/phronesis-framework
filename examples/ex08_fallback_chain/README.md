#

<div align="center">

# ex08 - fallback_chain

</div>

<div align="center">
  `runtime.Fallback`: primario falla, cache degradada cubre.
</div>

---

## Que demuestra

- `Fallback(primary=..., fallbacks=(...,))` cae al siguiente si el actual lanza.
- Sirve para degradar (cache, mirror, mock) sin propagar el error.

## Como correr

```bash
python -m examples.ex08_fallback_chain.main
```
