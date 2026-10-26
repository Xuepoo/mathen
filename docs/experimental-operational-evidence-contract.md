# Experimental and operational evidence contract

**Status:** additive MTH-0144 contract. This document defines how reviewed
cards may record observations; it does not promote research results or edit
canonical cards.

## Record identity and linkage

An evidence record keeps its stable, locally unique `id`. IDs are references,
not generated labels: a producer must not replace an existing ID when adding
metadata. A v1 observation sets `observation_version: "1"` and uses one of
`experiment`, `benchmark`, `fault-injection`, `operational-observation`,
`counterexample`, or `negative-result` as `kind`.

Every observation links its `workload`, `environment`, and `conditions` to the
same fixed system revision and protocol. `scope_context` is required and uses
the MTH-0143 states. A specified dimension cites local evidence IDs; unknown
means investigated but unresolved; unspecified means no claim was made; and
not-applicable requires a reviewed explanation. None of these states transfers
performance or failure behavior beyond the stated boundary.

The `provenance` object records a stable `run_id`, the same revision as
`system_commit`, a protocol digest, recording time, runner, and toolchain.
The digest and revision identify what was run; they do not establish that the
run was representative or causal.

## Results, nulls, and abstention

`result.status` is one of `observed`, `not-observed`, `inconclusive`,
`abstained`, or `failed`. Measurements have stable IDs, units, a status, and a
number or JSON null. A null is not zero: it represents not-observed,
not-measured, or abstained data. A measurement may use a number only when its
status is `observed`. An abstained result must state `abstention_reason`.

The record's `summary` describes only this run. `result_boundary.limits` must
state workload, environment, sampling, comparison, and other limits relevant
to interpretation. All v1 results are `canonical: false`, stored as
`research` or `draft`, and require human review before any card claim can cite
them.

No field in this contract means superiority, causality, universal
performance, or an automatic relation. A benchmark is an evaluation under a
protocol, not a ranking or proof. A failure is an observed behavior under a
trigger, not a universal failure mode. A counterexample records the target
claim, condition, observed result, and bounded implication. A negative result
records the question and what was not established, not that a system can never
do something.

## Artifacts and closure

Artifacts are explicit objects with a stable ID, kind, URI or local path, and
an optional digest. They identify logs, reports, datasets, configurations, or
other reproducibility material; an artifact reference is not proof that the
artifact is complete or independently verified.

`review.status` is `unreviewed` or `reviewed`. Unreviewed records cannot carry
card claim references. Reviewed records must name a reviewer, review time, and
at least one existing card claim reference (`card`, `feature:<id>`, or
`view:<model>`). This closure records human acceptance of the bounded wording;
it does not turn a result into a theorem or automatically alter a card.

## Compatibility and migration

- Legacy `experiment` records remain valid with their existing reproducibility
  fields. They are not silently interpreted as v1 observations.
- Existing source-code and official-doc evidence is not relabeled as an
  experiment, benchmark, operational observation, failure, counterexample, or
  negative result. A fixed commit or official document can support a documented
  mechanism or declared boundary, but not a measured workload result or
  operational rate without new evidence.
- A future migration may add v1 records or metadata only through reviewed edits
  that preserve stable IDs and cite local evidence. Missing fields become
  `unspecified` in an audit projection, never fabricated values or negative
  findings.
- Backfill tooling should emit proposals and a report of unresolved dimensions;
  it must not overwrite `data/systems/`, promote drafts, or infer conditions
  from names, URLs, source similarity, or default environments.
- Benchmark manifests may list `observation_evidence_ids`; the list must be
  unique and contained in the manifest evidence bundle. Existing manifests do
  not require it and remain valid.
