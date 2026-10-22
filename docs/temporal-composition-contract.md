# Temporal and Composition Contract

Architecture Cards may opt into a first structured contract for evolution and
composition. The fields are optional, so existing cards, draft files, CLI
commands, and API consumers remain valid without changes.

## Version context

`version_context` remains the backward-compatible human-readable version or
revision label. A card that needs structured temporal claims can add
`temporal_context`:

```json
{
  "version_context": "release 2",
  "temporal_context": {
    "version": "2.0",
    "valid_from": "2026-01-01",
    "status": "current",
    "supersedes": ["older-card"],
    "claim_status": "accepted",
    "evidence_ids": ["release-notes"]
  }
}
```

`status` describes the lifecycle position (`planned`, `current`, `superseded`,
`deprecated`, or `historical`). `claim_status` describes the review state of
the assertion and is independent of lifecycle status.

## Typed relations

`relations` is an optional list of typed, directed assertions. Each relation
has a target card ID, a claim type, review status, and at least one local
evidence ID:

```json
{
  "type": "extends",
  "target": "base-system",
  "claim_type": "inference",
  "claim_status": "under-review",
  "evidence_ids": ["design-doc"]
}
```

The initial vocabulary is deliberately small: `uses`, `extends`, `composes`,
`resembles`, and `influenced-by`. The existing `related_systems` array remains
unchanged for older, untyped links.

## Composition

An optional `composition` records a proposed or reviewed combination without
trying to execute it or prove its properties. It contains:

- `inputs`: one or more system IDs, their roles, optional input version context,
  review status, and evidence;
- `constraints`: conditions the composition must satisfy;
- `preserved_properties`: properties expected to survive composition;
- `conflicts`: incompatibilities, trade-offs, or unresolved tensions;
- `validation_gaps`: evidence or experiments still needed before the proposal
  can be accepted;
- `claim_status` and `evidence_ids` for the composition as a whole.

Every constraint, preserved property, conflict, and validation gap is a claim
with a description, `claim_type`, `claim_status`, and evidence IDs. Empty lists
are allowed for these categories so that a known absence is distinguishable
from an omitted contract. `validation_gaps` is optional for compatibility with
composition records written before this field existed.

## Validation and storage boundary

The JSON Schema defines shape and controlled vocabularies. Python semantic
validation additionally checks that every new evidence reference exists and
that composition inputs have unique IDs. D1 stores the three optional objects
as JSON columns (`temporal_context_json`, `relations_json`, and
`composition_json`) on `systems`; the existing scalar and
`related_systems_json` columns remain authoritative for legacy consumers.

The API returns the optional objects on `GET /api/systems/:id` and returns
empty/default values when an older row has no structured contract. No graph
database or graph-specific write API is introduced by this contract.
