# Evidence-bounded deployment and operating scope

**Status:** contract and corpus audit for MTH-0143. This document defines the
additive `scope_context` envelope; it does not backfill or promote cards.

## Contract

`scope_context` may be attached to a canonical card, feature, mathematical
view, evidence record, retrieval document, or benchmark deployment record. It
contains five independent dimensions:

| Dimension | Meaning | Examples of evidence | Does not establish |
| --- | --- | --- | --- |
| `validity_scope` | Systems, versions, deployment origins, conditions, and exclusions for the owning claim | versioned documentation, fixed-commit source, controlled experiment | that an unlisted system/origin is invalid |
| `workload` | Input, request, data, traffic, or use-case class under observation | benchmark dataset, workload specification, operational report | performance for another workload |
| `runtime_conditions` | Host, OS, dependencies, configuration, topology, resource limits, and execution mode | reproducible environment or deployment manifest | production behavior outside the observed conditions |
| `scale` | Quantity/unit and regime of the observation (for example, one process, node count, data volume, or request rate) | measured experiment, capacity document, explicit source statement | a universal capacity limit or scaling law |
| `failure_conditions` | Trigger, boundary, or failure model tested or explicitly documented | failure test, incident report, source-level failure path | absence of failures when no failure test was performed |

Each dimension is an object with `status`, `values`, and `evidence_ids`.
`status` is one of `specified`, `unknown`, `unspecified`, or
`not-applicable`:

- `specified` means the cited evidence supports the listed values;
- `unknown` means the dimension was investigated or is relevant, but the
  available evidence cannot establish a value;
- `unspecified` means no scope claim was made. It is the required migration
  representation for an unreviewed or absent dimension, not a negative
  finding;
- `not-applicable` means the reviewer explicitly determined that the dimension
  does not apply to this record and must explain that determination in `notes`.

Only `specified`, `unknown`, and `not-applicable` dimensions carry a claim
type, claim status, and non-empty local evidence IDs. `unknown` must remain an
explicit epistemic boundary; it must not be rewritten as `specified` from a
product name, category, deployment URL, source similarity, or default runtime.
`analogy` can describe a bounded comparison but cannot establish a validity
scope. The owning record's `fact`/`inference`/`hypothesis`/`analogy` type is not
upgraded by scope metadata.

The envelope is optional for compatibility. Once present, all five dimensions
are required. This makes partial coverage machine-visible without making every
existing card claim deployment or workload facts.

## Evidence and provenance rules

1. Every non-`unspecified` dimension cites IDs in the same evidence bundle as
   its owning record. A cited source may support only the dimension(s) actually
   stated in its notes or protocol.
2. `source-code` and `official-doc` evidence can establish a documented
   mechanism or declared boundary; they do not establish measured scale,
   workload performance, or production failure rates without corresponding
   evidence.
3. Experiment evidence must retain protocol, fixed system revision,
   environment, command, dataset, repetitions, metrics, and artifacts. These
   are observation provenance, not automatic scope claims.
4. Absence of a field in a legacy record is **absence of evidence**, not a
   negative finding. A negative finding requires a separately reviewed claim,
   its own evidence, and an explicit bounded failure condition.
5. Retrieval and benchmark metadata may carry `scope_context`, but must preserve
   evidence IDs, claim fields, source digest, and source reference. Indexes and
   manifests cannot fill missing dimensions or infer them during filtering.

## Compatibility and migration

- Existing `scope`, `validity_scope`, `deployment`, and retrieval filter fields
  remain valid. `scope_context` is additive and does not replace them.
- No canonical cards are backfilled by this task. Existing records therefore
  remain semantically unchanged and have five `unspecified` dimensions only in
  the audit projection, not stored in the cards.
- A future migration may add `scope_context` only through reviewed edits that
  cite local evidence. It must not manufacture `workload`, `scale`, or failure
  facts from names, categories, URLs, or source similarity.
- Migration `0007_evidence_scope_context.sql` adds nullable JSON metadata
  columns to `systems` and `evidence`; it performs no backfill. The seed and
  API/MCP paths preserve the envelope and `{"data": ...}` API success wrapper,
  while malformed metadata is omitted rather than repaired or synthesized.
- Benchmark and retrieval manifests can include the optional envelope. A
  producer that emits it must validate all five dimensions and close evidence
  IDs locally. Existing manifests remain valid.

## Corpus audit (canonical cards at this revision)

The audit scans `data/systems/*.json` at the task revision, without editing the
corpus. It counted **219 cards**, **830 features**, **608 mathematical views**,
and **1,531 evidence records**.

| Surface | Records with any existing structured scope | Records with deployment/workload/scale/failure fields |
| --- | ---: | ---: |
| Cards | 0 / 219 | 0 / 219 |
| Features | 0 / 830 | 0 / 830 |
| Mathematical views | 0 / 608 | 0 / 608 |
| Evidence | 0 / 1,531 | 0 / 1,531 |

There are **14 / 219** cards with `temporal_context`, and all **219 / 219** have
`version_context`; neither field is a substitute for deployment origin,
workload, runtime conditions, scale, or failure conditions. There are no
experiment evidence records (**0 / 1,531**), so the corpus currently has no
canonical measured workload/scale/failure coverage. The existing records are
**886 source-code** and **645 official-doc** evidence items.

Examples show why product-name inference is unsafe:

- DuckDB documents embedded execution and analytical workloads, but the card
  does not state a measured dataset, runtime, scale, or failure boundary.
- Firecracker describes multi-tenant cloud workloads and resource density, but
  does not specify an observed deployment origin, workload shape, scale, or
  failure test.
- CarryCtx documents a local-first/zero-network boundary, but that is a
  documented architectural claim, not evidence of every runtime condition or
  capacity regime.

These are missing/unknown scope observations, not findings that the systems do
not support other workloads, deployments, scales, or failure modes.

## Acceptance metrics and follow-up boundaries

Future reviewed additions should report, by surface and dimension:

- **coverage:** `specified / eligible records`, with `unknown`, `unspecified`,
  and `not-applicable` denominators shown separately;
- **evidence locality:** cited IDs found in the owning evidence bundle;
- **claim discipline:** independently reviewed agreement for claim type and
  status;
- **scope preservation:** retrieval/benchmark records whose envelope and
  source digest exactly match the source snapshot;
- **abstention:** queries or records withheld when an exact scope filter cannot
  be established; and
- **false-link rate:** independently reviewed links that incorrectly transfer
  scope between systems, features, or analogies.

Metrics with zero eligible observations must report a null value and denominator
zero; they must not be reported as zero coverage. A first implementation-ready
follow-up is a reviewed-card authoring/migration tool that emits an audit
report and proposes (but never writes) `scope_context`. Separate follow-ups are
needed for D1 migration/seed, API/MCP wire types, retrieval filtering, and
benchmark labels. This task does not perform those mutations, infer graph
relations, change Cloudflare resources, deploy, or promote cards.
