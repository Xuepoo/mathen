# MTH-0181 agent-review pilot

This research-only record captures an independent review of packet B from the
frozen MTH-0175 blinded study:

```text
data/research-review/pilots/mth-0181.json
```

The record is explicitly labeled `agent-review-pilot`, uses only packet B's
opaque reviewer key, and links to the frozen study with a canonical JSON
digest. The packet assignment snapshots provide prompts and references but do
not provide the referenced evidence payloads. Consequently, the review marks
evidence-dependent dimensions `unknown`, records abstention, and leaves no
dimension implicit. `unknown` is distinct from an absent `not-recorded`
label.

Its bounded execution provenance is `execution_actor: "llm-based-agent"`, with
`provider: "not-recorded"` and `model: "not-recorded"`. These fields describe
the executing LLM-based agent only; provider and model runtime provenance was
not recorded. They do not identify a model run or relabel this record as a
specific provider/model.

Validate the detached record without changing the frozen study or production
artifacts:

```bash
uv run python scripts/reviewer_pilot.py validate \
  data/research-review/mth-0175-study.json \
  data/research-review/pilots/mth-0181.json
```

The pilot is non-canonical and its promotion decision remains
`not-determined`. It is not human-review evidence.
