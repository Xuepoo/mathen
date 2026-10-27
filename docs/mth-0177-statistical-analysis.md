# MTH-0177 statistical error analysis

**Status:** research-only aggregation protocol. The checked-in artifact is
[`data/benchmark/mth-0177-statistical-analysis.json`](../data/benchmark/mth-0177-statistical-analysis.json).
Its contract is
[`schemas/statistical-analysis.schema.json`](../schemas/statistical-analysis.schema.json),
and its deterministic builder is
[`scripts/statistical_error_analysis.py`](../scripts/statistical_error_analysis.py).

## Purpose and boundary

MTH-0177 adds a statistical reporting layer over the accepted MTH-0174
cross-system task capacity and MTH-0172 candidate-quality dimensions. It does
not rewrite either artifact, canonical cards, API/MCP data, or paper text. The
artifact records the accepted MTH-0174 digest and commit as immutable source
metadata. The worktree used to author this task does not contain the accepted
MTH-0174 file, so its four domain slices and twelve task-card capacity are
retained from that digest without pretending that the source is locally
re-evaluated.

The checked-in result contains no repeated run, reviewer-label, or LLM-output
observations. Its metrics are therefore `null`, with denominator `0` and
status `not-evaluated`. The authored task repetitions are protocol capacity,
not independent observations and do not establish statistical power.

## Separate dimensions and slices

The error taxonomy is intentionally disjoint in reporting, while a single
observation may carry more than one explicitly observed error:

- **`false-link`:** An invalid relation or irrelevant link was returned.
- **`scope-loss`:** Task, system, deployment, workload, or temporal scope was
  omitted or changed.
- **`claim-discipline`:** Claim type/status/evidence discipline was changed or
  overstated.
- **`abstention`:** The method abstained on an eligible observation.
- **`counterexample-miss`:** An eligible counterexample or negative-knowledge
  target was missed.
- **`reviewer-disagreement`:** Explicit reviewer labels disagree for one
  observation.

Every observed row may carry `domain` and `task_id`; the builder emits separate
per-domain and per-task slices. No aggregate quality score is computed. Error
dimensions, candidate volume, reviewer effort, claim discipline, scope, and
counterexample handling remain separate questions.

## Interval policy

Binary rates use a Clopper–Pearson exact interval only when their denominator
is positive. Continuous repeated-run values use a deterministic percentile
bootstrap only when values are actually supplied. Empty denominators produce a
`null` value and `null` interval; they are never represented as zero. A measured
denominator below five gets an explicit `small sample` warning. Warnings do not
discard observations or imply statistical significance.

The functions `aggregate_rate`, `exact_binomial_interval`,
`bootstrap_interval`, `error_analysis`, and `repeated_run_aggregation` are
offline and deterministic. A future run should supply normalized observations
with provenance, run identity, task/domain identifiers, and reviewer-label
identity where applicable. Missing observations must remain missing.

## Reproduction and validation

```bash
python scripts/statistical_error_analysis.py
PYTHONPATH=src uv run python -m unittest tests.test_statistical_error_analysis -v
uv run ruff format --check scripts/statistical_error_analysis.py tests/test_statistical_error_analysis.py
uv run ruff check scripts/statistical_error_analysis.py tests/test_statistical_error_analysis.py
```

The script writes stable sorted JSON. It does not contact a provider, execute a
model, collect reviewer labels, or claim a result from protocol capacity alone.
