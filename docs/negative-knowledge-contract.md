# Negative-knowledge contract

Mathen records evidence-backed negative knowledge as standalone JSON documents
under `data/negative-knowledge/`. These records are review artifacts, not
Architecture Cards: the read-only API and canonical `data/systems/` boundary do
not promote them automatically.

## Contract

`schemas/architecture-negative-knowledge.schema.json` is versioned (`1.0`) and
each record must include:

- a kind: invalid composition, misleading similarity, scope violation, failed
  hypothesis, falsified experiment, retraction, or supersession;
- a bounded negative claim and explicit `scope` (systems, versions,
  deployment origins, conditions, and exclusions);
- top-level `claim_type`, `claim_status`, and non-empty local `evidence_ids`;
- one or more counterexamples, each with its own claim type/status, evidence,
  and an implication that explains what the counterexample prevents us from
  claiming;
- lifecycle links for retractions and supersession (`related_claim_ids`, plus
  `replacement_id` for supersession).

`bounded` is always `true`. The validator rejects broad universal wording such
as “all”, “always”, or “never” in `negative_claim`; a counterexample is not
evidence of absence and cannot be generalized beyond the declared scope.

Invalid compositions may additionally include `composition.inputs`,
`composition.operation`, and `composition.failure_mode`. These fields describe
the failed candidate without changing the typed-composition contract or
claiming a formal proof.

Representative boundaries include:

- append-only != immutable;
- replication != consensus;
- snapshot != transaction isolation;
- reconciliation != convergence proof.

Validate records with:

```bash
uv run mathen validate-negative-knowledge
```
