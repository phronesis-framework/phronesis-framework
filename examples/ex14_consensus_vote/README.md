#

<div align="center">

# ex14 - consensus_vote

</div>

<div align="center">
  `runtime.Consensus`: tres clasificadores votan; mayoria gana.
</div>

---

## Que demuestra

- `Consensus(voters=..., min_agreement=...)` agrega outputs en paralelo.
- Default: `majority_aggregator` devuelve el output mas repetido.
- Falla con `ConsensusError` si nadie alcanza `min_agreement`.

## Como correr

```bash
CASSETTE_PATH=examples/ex14_consensus_vote/cassette.jsonl \
  python -m examples.ex14_consensus_vote.main
```
