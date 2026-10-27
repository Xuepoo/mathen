# MTH-0183 collected observations

**Status:** research-only observation scoring. The checked-in artifact is
[`data/benchmark/mth-0183-collected-observations.json`](../data/benchmark/mth-0183-collected-observations.json),
validated by [`schemas/collected-observations.schema.json`](../schemas/collected-observations.schema.json)
and built by [`scripts/score_collected_observations.py`](../scripts/score_collected_observations.py).

## Boundary and provenance

MTH-0183 scores the accepted MTH-0180 packet-A and MTH-0181 packet-B detached
agent-review pilots through the MTH-0177 `error_analysis` primitive. Every row
preserves `reviewer_kind: "agent"` and `human_review: false`. These rows are
agent-run observations, never human reviewer evidence. The artifact has
separate `agent-review`, `human-review`, and `model-run` strata; the human-review
stratum is empty.

Both pilots supplied only prompts and opaque references. Candidate statements
and evidence payloads were missing, so evidence-dependent labels
(`evidence_support`, `claim_type`, `scope_completeness`, `false_link`, and
`counterexample_awareness`) could not be evaluated. The eight resulting rows
retain unknown labels and abstention observations. Per-pilot and per-task
slices remain available, and the observed elapsed times are retained only as
`agent-run` timing.

## Aggregation policy

The `abstention` dimension is measured for the eight actual agent rows and gets
the MTH-0177 Clopper–Pearson exact interval. Dimensions without an evaluated
payload have denominator zero, null value, and null interval. A measured
denominator below five emits the MTH-0177 small-sample warning; no rows are
discarded. The taxonomy remains separate and no aggregate quality score is
computed.

The direct-LLM attempt is a distinct `model-run` record with status
`not-evaluated` and null output metrics. No model runtime was available, so it
is not represented as a failure or as zero, and no model elapsed time is
invented.

## Reproduction

```bash
uv run python scripts/score_collected_observations.py
uv run python -m unittest tests.test_score_collected_observations -v
uv run ruff format --check scripts/score_collected_observations.py tests/test_score_collected_observations.py
uv run ruff check scripts/score_collected_observations.py tests/test_score_collected_observations.py
```

This process reads the accepted local artifacts only. It does not contact a
provider, alter canonical cards, write production records, or promote any
observation.
