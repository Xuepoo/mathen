# MTH-0118 benchmark harness

The research-only harness in `mathen.benchmark` turns the MTH-0118 plan into a
small executable boundary. It does not run an LLM, contact a deployment
origin, infer support from a URI, or promote a card.

It implements the pilot boundary described in
[`mth-0118-synthesis-validation-benchmark.md`](mth-0118-synthesis-validation-benchmark.md);
it is not an experiment result or a populated benchmark dataset.

## Manifest

`schemas/benchmark-run-manifest.schema.json` and
`src/mathen/benchmark.py` define version `1.0` run manifests. A manifest is an
audit record for one run and retains source revisions, an immutable evidence
bundle digest, all input IDs, method/baseline, model provenance, deployment
scope, randomness, candidates, review metadata, and a bounded outcome. Candidate
records require local evidence IDs and `proven: false`.

Validate a file or a directory of JSON manifests with:

```bash
uv run mathen validate-benchmark path/to/manifests
```

The validator is deliberately stricter than a JSON shape check: it rejects
dangling evidence IDs, duplicate IDs, incomplete model provenance, unbounded
candidate state, and undeclared fields. A successful validation is not an
experiment result.

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
- `counterexample_recall`, using held-out IDs as the reference set.

These helpers are intentionally small pilot primitives. Confidence intervals,
reviewer adjudication, baseline runners, and experiment execution remain future
research work described in the planning document.
