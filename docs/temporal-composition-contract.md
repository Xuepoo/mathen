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

## Typed composition semantics (additive 1.0 slice)

`composition.typed_semantics` is an optional, evidence-bounded interface
contract. It is defined by
[`schemas/architecture-typed-composition.schema.json`](../schemas/architecture-typed-composition.schema.json)
and checked by `mathen.typed_composition`. It does not replace the fields
above, and old cards remain valid.

The typed slice makes explicit:

- component `requires`, `provides`, and `consumes` obligations;
- declared adapters and inside/outside boundaries (never adapters inferred from
  names, vectors, graph position, or LLM prose);
- property effects: `shared`, `preserves`, `refines`, `weakens`, `strengthens`,
  and `unverified`;
- composition preconditions and postconditions;
- resource effects, failure modes, deterministic conflict explanations, and
  unresolved requirements;
- worked `examples`, `counterexamples`, `uncertainties`, and `disagreements`.

Typed candidates must retain `proven: false`. `validity_scope` includes systems,
versions, configurable deployment origins, conditions, and exclusions. Discovery
metadata records method, provenance, source and target communities, and the
cross-community path. This preserves the distinction between discovery and
validation: graphs and vectors expose candidate paths, LLMs retrieve/explain or
propose mappings, while contracts and experiments validate. A distant
cross-community candidate is valid input to review, not evidence of
compatibility.

The Python adapter is `adapt_typed_composition`; bounded exploration is
`solve_typed_compositions`. Both consume only explicitly declared typed fields.
They return review candidates and never promote a card, execute a component, or
claim a compatibility proof.

### Migration guidance

Existing cards need no migration. To adopt the slice, add
`composition.typed_semantics` alongside the existing composition fields, copy
only evidence-backed component interfaces into `components`, and keep the
legacy `constraints`, `preserved_properties`, `conflicts`, and
`validation_gaps` until reviewers have migrated their workflows. Put discovery
signals in `discovery` and unresolved interpretations in `uncertainties` or
`disagreements`; do not encode a graph/vector/LLM candidate as a validated
relation. Canonical cards remain under `data/systems/`; drafts and generated
typed candidates stay under configured draft locations.

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
