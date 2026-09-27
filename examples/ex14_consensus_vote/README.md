<div align="center">
  <img src="../../public/assets/lockup/lockup-horizontal-dark.png" alt="ex14 - consensus_vote" width="100%" />
</div>

<div align="center">

# ex14 - consensus_vote

</div>

<div align="center">
  `runtime.Consensus`: tres clasificadores votan; mayoria gana.
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

- `Consensus(voters=..., min_agreement=...)` agrega outputs en paralelo.
- Default: `majority_aggregator` devuelve el output mas repetido.
- Falla con `ConsensusError` si nadie alcanza `min_agreement`.

<div align="center">

## 🚀 Development setup

</div>

```bash
CASSETTE_PATH=examples/ex14_consensus_vote/cassette.jsonl \
  python -m examples.ex14_consensus_vote.main
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
