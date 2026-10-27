# MTH-0188 agent-review pilot scoring

MTH-0188 is a research-only scoring artifact for the two accepted enriched
packet pilots:

- [`mth-0186`](../data/research-review/pilots/mth-0186.json), packet A;
- [`mth-0187`](../data/research-review/pilots/mth-0187.json), packet B.

The checked-in artifact is
[`data/research-review/scoring/mth-0188-agent-review-scoring.json`](../data/research-review/scoring/mth-0188-agent-review-scoring.json).
Its contract is
[`schemas/agent-review-scoring.schema.json`](../schemas/agent-review-scoring.schema.json),
and its deterministic builder is
[`scripts/agent_review_scoring.py`](../scripts/agent_review_scoring.py).

## Boundary and provenance

The builder reads only the two accepted pilot artifacts. It records the pilot
file digest, enriched packet digest, candidate digest, evidence excerpt
digests, source IDs, negative-knowledge references and digests, scope context,
locality, and the observed timing supplied by each pilot. It preserves
`record_kind: agent-review-pilot`, `reviewer_kind: agent`,
`human_review: false`, and `agent-review-pilot` provenance.

The 16 rows present in the pilots are the evaluated observations. Both
`train` and `evaluation` rows are retained because they are observed pilot
rows; no holdout payload is read or copied. A holdout partition is rejected by
the builder. No canonical card, API, production, or paper file is written.

## Separate dimensions

The artifact reports independent label distributions for:

- evidence support;
- claim type;
- scope completeness;
- false link;
- usefulness;
- counterexample awareness;
- abstention; and
- reviewer effort.

Each distribution has an observed numerator and denominator, rate, status,
reason, and a 95% Clopper–Pearson exact interval. Intervals are emitted only
for denominators with actual evaluated rows. Task and agreement slices have
small-sample warnings because their denominators are below five; warnings do
not discard observations.

The artifact includes per-pilot, per-task, and per-domain slices. It computes
no aggregate quality score. The timing fields remain observations of the
source pilots' stated wall-clock scopes, not a claim about conversational
reasoning time or reviewer productivity.

## Agent-pilot agreement

The agreement section pairs A and B by task and reports separate agree/disagree
rates for every dimension. It is explicitly an `agent-pilot-agreement`
observation with `reviewer_kind: agent` and `human_review: false`. It is not
human reviewer agreement and must not be used as an estimate of human
reliability.

The artifact remains non-canonical, research-only, and promotion-neutral:
`promotion_decision` is `not-determined`, and no review result implies
promotion.

## Reproduction and validation

```bash
python scripts/agent_review_scoring.py
PYTHONPATH=src uv run python -m unittest tests.test_agent_review_scoring -v
uv run ruff format --check scripts/agent_review_scoring.py tests/test_agent_review_scoring.py
uv run ruff check scripts/agent_review_scoring.py tests/test_agent_review_scoring.py
```

The builder uses sorted, indented JSON with a final newline and no network,
provider, model, or human-review integration. Re-running it must preserve the
artifact byte-for-byte.
