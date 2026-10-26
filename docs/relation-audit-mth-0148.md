# MTH-0148 typed relation audit and safe expansion

## Scope and interpretation

This audit is a deterministic, read-only measurement of the reviewed
`data/systems/` corpus. It reads explicit card-level `relations` and reports
legacy `related_systems` separately. It does not edit cards, add edges, promote
proposals, or read drafts. Run it with:

```text
uv run mathen relation-audit data/systems \
  --output data/analyses/mth-0148-relation-audit.json
```

The report's `typed_coverage` means **review coverage**: the fraction of
reviewed cards participating in at least one valid, explicit typed relation.
Degree, component size, and high-degree rows mean **catalogue connectivity**.
They are not ecosystem centrality, importance, influence, completeness,
quality, or superiority. A singleton is not necessarily unimportant and a hub
is not necessarily important. Legacy navigation edges are not typed evidence.

## Current corpus snapshot

The current 219-card corpus contains 46 typed relations: 30 `uses`, 12
`resembles`, and 4 `composes`. All 46 are `proposed`; 34 carry `fact` and 12
carry `analogy`. All relation targets are reviewed cards and all evidence IDs
close to evidence owned by the source card. There are 59 systems participating
in a typed relation, giving 26.9406% review coverage, and 160 typed-edge
isolates. The valid typed graph has 46 directed edges and 177 undirected
components.

The separate combined navigation graph has 375 valid legacy edges and 411
unique directed edges after adding typed edges. It has 19 isolates and 27
undirected components, with a largest component of 186 cards. This connectivity
number must not be used to claim that the 186-card component is the ecosystem's
most important group; it only describes the current reviewed navigation data.

Typed high-degree patterns are similarly descriptive. `kubernetes` has the
largest typed degree (7 incoming); `carryctx`, `ionic`, `angular`, `sqlite`,
`vue`, `go`, `postgresql`, and `wayland` follow at degree 3. In the combined
navigation graph, `kubernetes`, `linux`, and `rust` have the largest degrees,
but legacy adjacency is not a dependency, influence, or importance signal.

## Relation closure and status semantics

For every typed relation, the audit checks:

1. `target` resolves to a reviewed card;
2. `evidence_ids` is non-empty and every ID is defined by the source card;
3. the type, claim type, and claim status are in the card contract; and
4. the direction and note remain source-card claims rather than inferred graph
   properties.

`proposed` means a candidate is recorded for deliberate review. It does not
mean accepted, true, complete, important, or recommended. Validation proves
shape and local evidence closure; it cannot prove the cross-card claim. The
other statuses retain their ordinary lifecycle meaning: `under-review` is
actively being assessed, `accepted` is a reviewer decision, `rejected` is a
review decision against the claim, and `deprecated` is retained history that
should not be treated as current support.

The current audit reports zero closure issues and zero same-pair type conflicts.
The conflict fixture deliberately shows the required abstention behavior.

The generated JSON report is intentionally written under the ignored
`data/analyses/` directory. This committed document records the reproducible
snapshot and policy; analysis artifacts remain rebuildable and are not
canonical card data.

The MTH-0143 `scope_context` contract is additive, but the current system
relation schema does not expose `scope_context` on relation objects: the audit
finds zero typed relations carrying it. A future relation-scope change must
define whether scope belongs to the relation itself or to its source evidence,
then update schema, validator, API/MCP projections, and tests together. Until
then, do not encode scope by inventing relation fields or by treating an
unscoped relation as universal.

## Safe proposal process

The only permitted automatic output is a review-only candidate/report. A
canonical relation proposal follows this sequence:

1. **Identify a reviewed target.** The target must already exist in the
   reviewed corpus. Missing targets are a catalog boundary, not permission to
   create a card or edge.
2. **Require explicit source evidence.** The source card must state the
   cross-system contract in evidence-bounded text. A target name, shared word,
   `related_systems` entry, model-family co-membership, vector similarity, or
   force-layout proximity is insufficient.
3. **Choose the narrowest supported type and direction.** Use `uses` for a
   documented source-to-target dependency/integration; `composes` for an
   explicitly assembled source around a target; `resembles` only for a bounded
   structural comparison (`claim_type: analogy`). `refines` is currently
   available only for feature relations; adding it to system relations requires
   an explicit schema and validator decision. Do not infer `extends` or
   `influenced-by` without dedicated evidence for inheritance or historical
   lineage.
4. **Preserve provenance.** Copy only evidence IDs present in the source card.
   Preserve validity/scope and write a boundary note naming what the claim does
   not assert. Keep the candidate `claim_status: proposed`.
5. **Check conflicts and reverse claims.** If the same directed pair has
   multiple types, evidence conflicts, incompatible scopes, or a reverse edge
   that changes the claim, abstain and ask for review. Do not resolve conflict
   by score, popularity, degree, or a graph algorithm.
6. **Review separately.** A human reviewer accepts, rejects, or defers the
   candidate and edits the canonical card. Re-run validation and this audit
   after an explicit edit. Candidate generation never mutates canonical JSON.

### Mandatory abstentions

Abstain when evidence is absent, foreign to the source card, only a generic
keyword, only a legacy navigation link, only a mathematical-model grouping,
only a vector/layout result, the target is missing, the direction is unclear,
the claim would assert universality beyond a scoped deployment, or relation
types/statuses conflict. `tests/fixtures/relation-audit-abstention.json` and
`relation-audit-conflict.json` are executable documentation for these cases.

## Algorithm boundaries

Reusable graph algorithms are useful for navigation and analysis only:

- **Shortest path:** navigate explicit edges (with an explicit choice of
  typed-only or combined-navigation graph). A path is not proof of dependency,
  causation, influence, or transitive relation closure. Do not serialize a path
  as a new edge.
- **Community detection:** summarize clusters for browsing or review queues.
  Communities depend on the selected edge layer, direction handling,
  resolution, and algorithm; membership is not an architectural category or
  evidence-backed relation.
- **Vector calculations:** calculate embeddings/similarity for search and
  navigation candidates only. Similarity is not `resembles`, and it cannot
  establish `uses`, `composes`, `refines`, influence, importance, or
  superiority. Vectors must not mutate cards or relation stores.

All three algorithms must consume a snapshot, return an analysis artifact, and
remain outside canonical card validation and seed/promotion paths. Their
outputs must carry the selected layer, algorithm, parameters, and snapshot
identity, and must be labelled navigation/analysis rather than evidence.

## Implementation-ready follow-ups

- Add a read-only graph query surface with explicit `layer=typed|navigation`
  and bounded shortest-path queries. Return path nodes/edges plus a warning
  that the result is navigation, never a relation proposal.
- Add deterministic community-analysis output under `data/analyses/`, with
  algorithm/version/parameters and no card write path. Test that changing the
  layer changes the analysis but not canonical files.
- Add vector-search result metadata that records model/version and similarity
  parameters. Keep vectors in a rebuildable index and expose results as
  candidates only.
- If system-level `refines` is desired, first define its direction, claim-type
  constraints, evidence and scope semantics in the JSON schema, Python
  validator, API/MCP projection, and tests. Do not overload feature-level
  `refines`.
- Close the existing layered graph transport gap separately: project explicit
  card relations with target existence checks while preserving source metadata;
  this is transport work, not a reason to add edges.
