# MTH-0185 enriched research review packet

MTH-0185 is a deterministic, research-only enrichment of the accepted
MTH-0174 cross-system task set and frozen MTH-0175 blinded-study assignment
contract. The checked-in artifact is
[`data/research-review/mth-0185-enriched-study.json`](../data/research-review/mth-0185-enriched-study.json).
Its contract is
[`schemas/enriched-review-packet.schema.json`](../schemas/enriched-review-packet.schema.json),
and its offline builder and validator are
[`scripts/enriched_review_packet.py`](../scripts/enriched_review_packet.py).

## Enriched assignment contract

Every assigned non-holdout item contains:

- an authored candidate statement, candidate ID and candidate digest;
- claim type, `proven: false`, system/task scope and source IDs;
- local evidence IDs with a short payload excerpt, claim type, source/card ID,
  source reference and excerpt digest;
- explicit candidate/evidence locality metadata; and
- references to the bounded negative-knowledge record and its counterexamples.

The packet source digests identify the accepted benchmark, frozen study,
negative-knowledge input and reviewed cards. Candidate and evidence excerpt
digests are calculated separately, so a source digest cannot be mistaken for a
candidate or evidence digest.

## Blind balance and holdout isolation

Two opaque reviewer keys receive the same eight non-holdout assignments in
seeded deterministic but independently shuffled order. Packet labels A and B,
the seed, study/protocol versions and overlap policy are explicit. The four
MTH-0174 holdout task IDs are recorded only in isolation metadata. Holdout
candidate, evidence, prompt and negative-knowledge content is not copied into
either packet.

No reviewer labels, human evidence, LLM output, empirical result or promotion
decision is generated. The frozen MTH-0175 study is referenced by digest and is
not modified.

## Validation

```bash
uv run python scripts/enriched_review_packet.py
uv run python scripts/enriched_review_packet.py \
  --validate data/research-review/mth-0185-enriched-study.json
```

The builder is deterministic and offline. It reads current reviewed cards and
the bounded negative-knowledge record only to construct local excerpts. It does
not write canonical cards, drafts, APIs, MCP data, migrations, relations,
production records or paper text.
