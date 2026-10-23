# Extraction quality and coverage

Mathen's deterministic repository inspection is useful for finding stable
source boundaries, but it is not a semantic architecture extractor. The
modeling stage must therefore review coverage against evidence instead of
equating a path signal, file count, or category label with an architecture
claim.

## Current collection baseline

The reviewed collection currently contains **154 cards**. A reproducible count
of `data/systems/*.json` on 2026-10-23 found this feature distribution:

| Features per card | Cards |
| ---: | ---: |
| 2 | 4 |
| 3 | 74 |
| 4 | 66 |
| 5 | 5 |
| 6 | 3 |
| 8 | 2 |

Thus **140 of 154 cards (90.9%) have three or four features**. This is a
review signal, not a target quota: a small card can be correct when its scope
is narrow, and a larger card can still be shallow. The Temporal correction
adds independently meaningful boundaries because the evidence supports them;
it does not treat the frontend's displayed domain count as card metadata.

## Systematic limitations

The current cards and extraction workflow have several known limitations:

- **Shallow structural relations.** Only 3 of 154 cards currently contain a
  `relations` array, with four total relations (`composes`: 1,
  `resembles`: 3). Shared feature vocabulary and `related_systems` entries do
  not establish an architectural relation, and source evidence for a relation
  must support the relationship itself.
- **Inconsistent taxonomy.** Feature categories are descriptive strings rather
  than a controlled ontology. The current collection has many one-off labels;
  similar concepts can appear under different names, while the same category
  can contain different abstraction levels. Category frequency is therefore a
  discovery aid, not a quality score.
- **Domain coverage is uneven.** Scope strings are card-specific labels, not a
  normalized domain inventory. A missing or short scope does not prove that a
  system lacks a domain, and a populated scope does not show how a domain is
  implemented.
- **Component roles are easy to collapse.** Repository paths identify likely
  components but do not explain ownership, state, interface direction,
  placement, or failure behavior. Review must distinguish gateways, durable
  state owners, schedulers, workers, caches, and external dependencies when
  evidence supports those roles.
- **Temporal evidence boundaries are real.** Documentation is versioned and
  may describe current Cloud or server behavior. A card with a pinned source
  revision records documentation access dates and must not apply a later
  guarantee to that revision without corroborating source evidence.
- **Negative claims are underdetermined.** Deterministic reports usually show
  what was inspected, not everything the system can do. “Unknown” and
  “out-of-scope” are valid review outcomes and should not be silently turned
  into absence claims.

## Coverage review protocol

For each modeling bundle, review the following dimensions independently:

1. domains and components;
2. state and lifecycle;
3. interfaces and dependencies;
4. consistency and ordering;
5. security and boundaries;
6. failure and recovery;
7. resources and scale;
8. evolution and compatibility;
9. transferable architecture patterns.

For each dimension, record a supported claim with evidence IDs, or explicitly
record that it is unknown or out of scope. Features should capture a distinct
boundary, mechanism, state transition, or trade-off. Mathematical views must
answer a concrete question and state assumptions, limits, and counterexamples.
Do not add features to meet a fixed count.

The modeling prompt contract in `src/mathen/modeling.py` carries this protocol
into generated drafts. Generated drafts remain under `data/drafts/` and require
human review before any canonical-card promotion.

## Reproducibility

The baseline can be recomputed without changing cards:

```bash
uv run python - <<'PY'
import json
from collections import Counter
from pathlib import Path

cards = [json.loads(path.read_text()) for path in Path("data/systems").glob("*.json")]
print(len(cards), Counter(len(card["features"]) for card in cards))
print(sum(bool(card.get("relations")) for card in cards))
print(sum(len(card.get("relations", [])) for card in cards))
PY
```
