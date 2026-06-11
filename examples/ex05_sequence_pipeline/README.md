#

<div align="center">

# ex05 - sequence_pipeline

</div>

<div align="center">
  Pipeline lineal con `runtime.Sequence`: researcher -> writer -> editor.
</div>

<div align="center">
  <a href="../README.md">examples</a> ·
  <a href="../../src/phronesis/runtime/modes/sequence.py">source</a>
</div>

---

## Que demuestra

- `Sequence(nodes=(a, b, c))` ejecuta los nodos en orden.
- La salida de cada nodo se pasa como `input` al siguiente.
- `ExecutionContext.new()` como contexto raiz.

## Como correr

Cassette:

```bash
CASSETTE_PATH=examples/ex05_sequence_pipeline/cassette.jsonl \
  python -m examples.ex05_sequence_pipeline.main
```

Ollama:

```bash
python -m examples.ex05_sequence_pipeline.main
```
