# MTH-0195 independent cross-system exploration benchmark

**Status:** research-only authored task set. The artifact contains no model
outputs, reviewer labels, prototype observations, empirical scores, or
superiority claim.

The machine-readable artifact is
[`data/benchmark/mth-0195-independent-exploration.json`](../data/benchmark/mth-0195-independent-exploration.json).
Its schema is
[`schemas/independent-exploration-benchmark.schema.json`](../schemas/independent-exploration-benchmark.schema.json),
and its deterministic builder is
[`scripts/build_mth0195_benchmark.py`](../scripts/build_mth0195_benchmark.py).

## Independent task design

MTH-0195 contains 24 independently authored task instances across four
domains. Every instance has a unique task key, question, evidence slice,
input digest, source-revision digest, and reviewed-card digest list. The task
keys are not repeated replicates. This is a design property of the authored
fixture, not a claim of statistical power or independent empirical samples.

| Domain | Reviewed systems | Tasks | Kinds |
| --- | --- | ---: | --- |
| Storage | SQLite, PostgreSQL, DuckDB | 6 | all five kinds |
| Streaming | Kafka, Temporal | 6 | all five kinds |
| Orchestration | Kubernetes, Airflow, Crossplane | 6 | all five kinds |
| Isolation | Firecracker, Git, CarryCtx | 6 | all five kinds |

Positive tasks are train candidates, composition tasks are evaluation tasks,
and negative, unknown, and counterexample tasks are holdout tasks. The
partition map is exhaustive and disjoint. Every holdout task is excluded from
candidate generation; negative and counterexample tasks additionally appear in
the negative-knowledge holdout list.

## Evidence and candidate boundary

Evidence records copy only IDs and metadata from reviewed cards or the reviewed
negative-knowledge boundary. Each task records the exact local evidence IDs it
may use. Source and card bytes are hashed into the artifact, and task input
digests make accidental repetition visible to validation.

Future composition candidates must remain `claim_status: proposed`,
`canonical: false`, and `proven: false`. A composition task is a prompt for a
bounded candidate with stated interfaces, obligations, and uncertainty; it is
not a compatibility proof, production recommendation, or architecture card.

## Evaluation boundaries

Direct-LLM is explicitly present but `not-evaluated`. No provider, model,
prompt, runtime, or output is asserted. All metric denominators are zero and
values are null because no labels or observations are supplied. The artifact
does not claim truth, compatibility, causality, originality, production
readiness, model quality, or superiority over any baseline.

Regenerate and validate the exact artifact with:

```bash
python scripts/build_mth0195_benchmark.py
python scripts/build_mth0195_benchmark.py \
  --validate data/benchmark/mth-0195-independent-exploration.json
```

The builder is deterministic and offline. It does not contact a provider,
deployment origin, API, MCP server, or production corpus.
