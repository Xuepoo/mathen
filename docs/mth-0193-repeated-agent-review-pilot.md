# MTH-0193 repeated agent-only review pilot

MTH-0193 records two independent, research-only observations over the
MTH-0185 enriched packet. The checked-in artifact is
`data/research-review/pilots/mth-0193.json`. Its contract is
`schemas/repeated-agent-review-pilot.schema.json`, and its offline runner and
validator are `scripts/repeated_agent_review_pilot.py`.

## Independent runs

The artifact contains two distinct run IDs and seeds:

- `mth-0193-run-alpha` processes packet order `A`, then `B`;
- `mth-0193-run-beta` processes packet order `B`, then `A`.

Within each packet, a seed-specific shuffle changes the assignment order. Each
run records observed wall-clock timing for the run and each supplied-payload
observation. Timing covers packet payload handling only; it excludes
conversational reasoning, human review, and reviewer productivity claims.

Every packet and observation retains the exact MTH-0185 packet digest, source
digest, candidate digest, evidence excerpt digests, assignment IDs, candidate
statement and claim type, evidence IDs, source IDs, scope context, locality,
and negative-knowledge references/digests. The runner verifies these closures
against the checked-in MTH-0185 packet and the MTH-0186/MTH-0187 pilot
contracts before writing the artifact.

## Boundary and interpretation

Every artifact, run, packet record, and observation explicitly states
`reviewer_kind: "agent"`, `human_review: false`, `research_only: true`,
`non_canonical: true`, and `promotion_decision: "not-determined"`. The
observations are not human review, human labels, agreement, promotion, or
canonical evidence. No canonical, API, MCP, migration, relation, production,
or paper file is written.

The source contracts' evidence-dependent labels are copied without conversion.
In particular, `unknown` and abstention values are not replaced with positive
judgments, and missing evidence is not treated as support. The runner does not
read or copy holdout candidate, evidence, or negative-knowledge content.

## Reproduction and validation

```bash
uv run python scripts/repeated_agent_review_pilot.py
uv run python scripts/repeated_agent_review_pilot.py \
  --validate data/research-review/pilots/mth-0193.json
PYTHONPATH=src uv run python -m unittest \
  tests.test_repeated_agent_review_pilot -v
uv run ruff format --check scripts/repeated_agent_review_pilot.py \
  tests/test_repeated_agent_review_pilot.py
uv run ruff check scripts/repeated_agent_review_pilot.py \
  tests/test_repeated_agent_review_pilot.py
```

Because observed timestamps and elapsed wall-clock values are recorded, a new
execution is a new observation artifact rather than a byte-identical rebuild.
