# G6 relation-candidate report

`mathen relation-candidates` generates a deterministic, review-only report from
Architecture Cards. It does not edit `data/systems/`, add a `relations` array,
or assign an accepted/proposed canonical edge.

```bash
uv run mathen relation-candidates
```

The default output is `data/analyses/g6-relation-candidates.json`. This path is
ignored because the report is reproducible analysis output. A different card
directory and output path can be selected explicitly:

```bash
uv run mathen relation-candidates data/systems \
  --output data/analyses/g6-relation-candidates.json
```

## Signals and boundaries

The generator uses only high-confidence, card-visible signals:

- `related_systems` produces a navigation candidate, not a typed relation;
- an exact source-local target mention in an evidence-backed descriptive field
  produces a stronger signal only when it appears near an explicit
  integration/dependency cue such as `uses`, `depends on`, or `integrates with`;
- target aliases are the target ID, its hyphen-to-space form, and the reviewed
  target card's exact `name`;
- existing typed relations suppress the corresponding `(source, target)` pair;
- self-links are ignored; feature names, categories, summaries, shared
  vocabulary, and fuzzy/token-only matches are ignored.

Evidence IDs in `evidence_candidates` are copied only from the source claim and
are never taken from the target card. A mention without an evidence ID that is
present in the source card cannot create a candidate. A `related_systems` entry
whose target card is absent remains visible with `status: "missing-target"` so
that review can resolve the catalog boundary.

## Report shape

The report contains `analysis_version`, sorted `card_ids`, an inventory of
existing typed relations, deterministic scoring weights, and sorted
`candidates`. Each candidate contains:

| Field                 | Meaning                                                                                    |
| --------------------- | ------------------------------------------------------------------------------------------ |
| `source`, `target`    | Directed card IDs or a missing target ID                                                   |
| `target_exists`       | Whether the target is present in this card set                                             |
| `status`              | `needs-review` or `missing-target`                                                         |
| `reasons`             | Ordered signals: `related_systems`, `source_local_target_mention`, and/or `missing_target` |
| `score`               | 70 for an evidence-bound mention plus 30 for `related_systems`                             |
| `evidence_candidates` | Sorted source-local evidence IDs suitable for human review                                 |

Candidates are merged by directed `(source, target)` pair. The score ranks
review work; it is not a probability or a semantic confidence proof. Human
review must choose the relation type, claim type, notes, status, direction, and
whether any canonical card edit is justified. The report intentionally cannot
distinguish a universal dependency from an optional integration when the card
does not state that boundary.
