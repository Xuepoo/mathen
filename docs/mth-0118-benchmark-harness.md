# MTH-0118 benchmark harness

The research-only harness in `mathen.benchmark` turns the MTH-0118 plan into a
small executable boundary. It does not run an LLM, contact a deployment
origin, infer support from a URI, or promote a card.

It implements the pilot boundary described in
[`mth-0118-synthesis-validation-benchmark.md`](mth-0118-synthesis-validation-benchmark.md);
it is not an experiment result or a populated benchmark dataset.

## Manifest

`schemas/benchmark-run-manifest.schema.json` and
`src/mathen/benchmark.py` define version `1.1` run manifests. A manifest is an
audit record for one run and retains source revisions, an immutable evidence
bundle digest, all input IDs and per-input evidence closure, method/baseline,
model provenance, deployment scope, randomness, explicit train/evaluation/holdout
partitions, temporal leakage controls, novelty reference scope, analogy
boundaries, candidates, review metadata, and a bounded outcome. Candidate
records require local evidence IDs and `proven: false`; `result_boundary` keeps
all output in research/draft scope and rejects canonical promotion.

Validate a file or a directory of JSON manifests with:

```bash
uv run mathen validate-benchmark path/to/manifests
```

The validator is deliberately stricter than a JSON shape check: it rejects
dangling evidence IDs, missing input-to-evidence links, digest mismatch,
overlapping or incomplete split partitions, temporal splits without a cutoff,
exposed negative-knowledge holdouts, duplicate IDs, incomplete model
provenance, unbounded candidate state, aggregate novelty scores, unsafe analogy
claims, canonical result boundaries, and undeclared fields. A successful
validation is not an experiment result.

## Deterministic metrics

Metric helpers accept normalized records and explicit reviewer/check judgments;
they never decide whether prose or a URL is evidence. Every result preserves a
numerator and denominator, and an empty denominator has value `null`:

- `evidence_locality` and `citation_precision`;
- `claim_discipline`, including claim-type accuracy and unsupported rates by
  claim type;
- `classification_metrics` for `valid`, `invalid`, and `undetermined`, with a
  confusion matrix and per-outcome precision/recall;
- `typed_obligation_satisfaction`, requiring exact provisions or an explicit
  adapter;
- `counterexample_recall`, using held-out IDs as the reference set;
- `heldout_counterexample_recall`, which rejects a run when held-out negative
  knowledge was exposed to generation;
- selective classification metrics: abstention rate, coverage, known-case
  accuracy, and unknown recall; empty denominators remain `null`;
- `novelty_scope_completeness`, requiring a dimension-specific reference
  window, representation, scope, falsifiers, and a non-fact claim type.

These helpers are intentionally small pilot primitives. Confidence intervals,
reviewer adjudication, baseline runners, and experiment execution remain future
research work described in the planning document.

## Retrieval evaluation contract (MTH-0134)

`schemas/retrieval-evaluation-manifest.schema.json` and the retrieval functions
in `mathen.benchmark` define a separate `retrieval_evaluation` manifest at
schema version `1.0`. It is an extension of the research harness, not a change
to the existing `1.1` synthesis manifest and not a retrieval backend.

Validate it with:

```bash
uv run mathen validate-retrieval-evaluation data/benchmark/retrieval
```

The contract freezes a reviewed `canonical_cards` corpus snapshot and a
deterministically digested query set. Corpus documents retain stable IDs,
source references/digests, claim types/statuses, evidence IDs, and version and
deployment-origin scope. Query labels are separate from the corpus and record
graded relevance, evidence locality, scope match, and label provenance. A
three-way query split is disjoint and exhaustive; held-out negative-knowledge,
counterexample, and unknown labels are explicitly excluded from candidate
generation.

Method, provider/model, representation, dimensions, distance metric, and prompt
metadata are recorded even when a method does not use an embedding model. The
novelty boundary declares all six dimensions without allowing an aggregate
novelty score. Analogy boundaries require non-equivalence, direct evidence for
historical influence, and no implied substitutability. Results must hydrate
reviewed corpus IDs and preserve source/evidence/scope metadata; draft IDs,
missing evidence closure, duplicate ranks, and unbounded output are rejected.

The permitted metrics are bounded **discovery** metrics only: recall@k, nDCG@k,
evidence locality, claim-type accuracy, scope completeness, false-link rate,
and abstention rate. Every metric retains numerator, denominator, and a null
value for an empty denominator. These metrics do not establish retrieval
quality, truth, compatibility, causality, or originality. The result boundary
requires `canonical: false`, research/draft storage, human review before any
promotion, and explicitly marks scores as neither truth nor compatibility.

## Reproducibility and leakage checklist

Before treating a manifest as an input to analysis, verify that:

1. every source revision has an immutable commit or archive digest;
2. `provenance.input_bundle_digest` equals `evidence_bundle.digest`;
3. every declared input has at least one evidence ID in `input_evidence`;
4. train, evaluation, and holdout references are disjoint and exhaustive;
5. temporal splits record a cutoff and the leakage controls used;
6. every negative-knowledge input is in the holdout and excluded from candidate
   generation;
7. novelty is reported by dimension and declared strata, never as an aggregate;
8. analogies explicitly retain non-equivalence and do not imply influence or
   substitutability; and
9. results remain non-canonical until a separate human review promotes them.
