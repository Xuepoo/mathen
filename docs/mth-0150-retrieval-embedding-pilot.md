# MTH-0150 Retrieval Embedding Pilot

**Status:** Research-only offline pilot; not a production index decision.

## Protocol

- Corpus: reviewed `canonical_cards` records from 219 cards.
- Documents: 2,481 deterministic atomic retrieval documents.
- Queries: 12 manually authored architecture-discovery questions spanning control
  loops, logs, MVCC, sandboxing, compiler IR, recovery, replay, container
  layers, content-addressed storage, runtime state, and serialization
  dependencies.
- Control: the deployed bounded lexical ranking behavior.
- Candidate: local `bge-micro-v2` ONNX file with mean pooling, L2
  normalization, and cosine similarity.
- Runtime: Transformers.js 4.3.1 with `onnxruntime-node` 1.30.0.
- Corpus digest:
  `sha256:f935de7a8f1bb91a0d139e959ffabbeab30d2e42dc91343c7514810db436f4a9`.

The full machine-readable record is
`docs/audits/mth-0150-retrieval-embedding-pilot.json`.

## Results

| Method | Recall@5 | nDCG@5 |
| --- | ---: | ---: |
| Lexical baseline | 10/12 = 0.8333 | 0.5579 |
| Local vector candidate | 10/12 = 0.8333 | 0.5464 |

The vector candidate did not improve either measured discovery outcome in this
pilot. Its document embedding pass took approximately 280.8 seconds on CPU
for 2,481 documents. The RTX 4060 Laptop GPU was present, but the installed
Node ONNX runtime could not load its CUDA provider because the required shared
provider library was unavailable; no GPU timing is claimed.

## Decision

Keep the deployed bounded lexical baseline. Do not add embeddings, Vectorize, a
provider binding, a secret, or a production vector index based on this result.
A larger, reviewer-labeled evaluation with paraphrase,
misleading-similarity, claim-type, scope, freshness, abstention, latency, and
cost slices would be required before reconsideration.

This pilot is discovery-only. Similarity does not create graph relations or
establish truth, compatibility, causality, historical influence,
substitutability, originality, or architectural superiority. No canonical
cards, drafts, relations, or production resources were changed by the pilot.
