# MTH-0159 research review queue audit

`scripts/audit_research_review_queue.py` produces a deterministic, read-only
projection of the latest canonical corpus and research artifacts. By default
it reads `origin/main` through `git show`; it does not checkout a ref or edit
the worktree.

```bash
uv run python scripts/audit_research_review_queue.py \
  --ref origin/main \
  --output /tmp/opencode/mth-0159-review-queue.json
```

The report covers:

- `scope_context` coverage for cards, features, mathematical views, and
  evidence. Missing dimensions are `not-recorded`; explicit `unknown`,
  `unspecified`, `not-applicable`, and `specified` statuses remain distinct.
- Feature and mathematical-view lifecycle records, including every missing
  lifecycle envelope and every explicitly recorded status. Missing metadata is
  not treated as proposed, observed, reviewed, current, or absent.
- Version-1 observation artifacts under `data/experiments/`, with their
  explicit review status, explicit card-claim references, research boundary,
  human-review promotion gate, and whether the observation ID is linked from a
  canonical evidence bundle. The artifact remains physically detached from
  the card corpus even when a reviewed card has copied the evidence record;
  neither presence nor linkage is treated as promotion.
- Standalone mathematical-view contracts under `data/mathviews/`, their
  deterministic validation result, and each `validation_record`. A `valid`
  classification is a bounded consistency result, not a review or promotion
  decision.
- Existing typed relations and deterministic relation candidates. Candidates
  remain separate from existing relations and are never written to cards.

The JSON includes the resolved source commit and explicit false mutation and
non-inference guardrails. It does not infer scope, lifecycle, review,
promotion, relation type, historical influence, or negative findings from
missing evidence, names, claim types, source kinds, graph topology, or
deterministic classifications.
