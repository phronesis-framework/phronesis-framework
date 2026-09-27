<div align="center">
  <img src="../../public/assets/lockup/lockup-horizontal-dark.png" alt="ex05 - sequence_pipeline" width="100%" />
</div>

<div align="center">

# ex05 - sequence_pipeline

</div>

<div align="center">
  Pipeline lineal con `runtime.Sequence`: researcher -> writer -> editor.
</div>

<div align="center">
  <a href="../../src/">source</a> · <a href="../../tests/">tests</a> · <a href="../../docs/">docs</a> · <a href="../">examples</a>
</div>

<br />

<div align="center">
  <a href="https://go-skill-icons.vercel.app/">
    <img src="https://go-skill-icons.vercel.app/api/icons?i=python,typescript,react,nextjs,git&titles=true" alt="Technology stack" />
  </a>
</div>

---

<div align="center">

## 🎯 Purpose

</div>

- `Sequence(nodes=(a, b, c))` ejecuta los nodos en orden.
- La salida de cada nodo se pasa como `input` al siguiente.
- `ExecutionContext.new()` como contexto raiz.

<div align="center">

## 🚀 Development setup

</div>

Cassette:

```bash
CASSETTE_PATH=examples/ex05_sequence_pipeline/cassette.jsonl \
  python -m examples.ex05_sequence_pipeline.main
```

Ollama:

```bash
python -m examples.ex05_sequence_pipeline.main
```

<div align="center">

## ✅ Expected output

</div>

The example prints its execution result. The exact output depends on the selected provider and input; see [`main.py`](main.py) for the result handling.

<div align="center">

## 📚 Documentation

</div>

- [Example implementation](main.py)
- [Examples catalog](../README.md)
