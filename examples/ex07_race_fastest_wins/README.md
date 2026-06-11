#

<div align="center">

# ex07 - race_fastest_wins

</div>

<div align="center">
  `runtime.Race`: cache rapida vs upstream lento. Gana el primero.
</div>

---

## Que demuestra

- `Race(nodes=...)` corre los nodos en paralelo y devuelve el primero.
- Cancela los demas en cuanto hay ganador.
- `callable_node(async_fn)` envuelve coroutines en `Executable`.

## Como correr

```bash
python -m examples.ex07_race_fastest_wins.main
```

Sin cassette: los dos nodos son funciones puras-Python, deterministicas.
