<!-- markdownlint-disable MD013 -->

# Mathen multi-paper planning outlines

**Status:** internal planning artifact only; no paper正文, LaTeX, BibTeX,
figures, author metadata, or submission tooling.

This document is a lightweight outline for a possible sequence of papers. It is
not a manuscript, literature review, evaluation report, novelty statement, or
promotion decision. Findings are provisional and remain bounded by the exact
artifacts in the [evidence index](#compact-evidence-index). The internal
literature map in [`paper/README.md`](README.md) is preserved unchanged and
remains the bounded prior-art map.

## Interpretation guardrails

- Evidence paths below are repository paths, not claims that every historical
  artifact is present in the current baseline. MTH-0201 records absent or
  partial historical artifacts explicitly; absence is not reconstructed here.
- The current wave is research-only, non-canonical, and promotion-neutral.
  `fact`, `inference`, `hypothesis`, and `analogy` must remain distinct in any
  later manuscript.
- MTH-0186, MTH-0187, MTH-0188, MTH-0193, and the associated MTH-0177/MTH-0196
  observations are **agent-only, non-human observations**. They are not human
  labels, human agreement, reviewer productivity, or evidence of model quality.
- Human review is optional and deferred. The MTH-0175 protocol has no completed
  human labels, and no human result may be inferred from an empty stratum.
- Direct-LLM remains **not evaluated**. MTH-0176 defines a control boundary and
  MTH-0194 records local readiness, but neither supplies a direct model run.
- No outline supports a novelty, superiority, causality, generalization,
  compatibility, production-readiness, or proof claim.

## Paper 1 — evidence-bounded Architecture Exploration instrument

### Paper 1 working title

**An Evidence-Bounded Architecture Exploration Instrument for Reproducible
Cross-System Knowledge**

### Paper 1 research question

Can a repository-centered instrument make small architecture features,
relations, candidate views, negative knowledge, scope, and provenance explicit
enough to support reproducible exploration without presenting generated
candidates as reviewed facts or proofs?

### Paper 1 current findings (provisional)

- The evidence wave specifies an instrument boundary rather than an outcome
  claim: research-only artifacts retain fixed paths, source revisions,
  digests, validation commands, review state, and promotion boundaries in
  [`data/reproducibility/mth-0201-reproducibility-index.json`](../data/reproducibility/mth-0201-reproducibility-index.json)
  (MTH-0201).
- The historical MTH-0169 exploration fixture and MTH-0172 candidate-quality
  evaluation are recorded as not present in the indexed baseline, so they
  provide protocol lineage but no current measured result:
  `data/benchmark/mth-0169-exploration.json` and
  `data/benchmark/mth-0172-candidate-quality.json` (MTH-0169, MTH-0172;
  absence recorded by MTH-0201).
- The historical MTH-0174 cross-system task set is likewise indexed as absent:
  `data/benchmark/mth-0174-cross-system.json` (MTH-0174). Its task capacity
  must not be reported as empirical quality or statistical power.
- [`data/research-review/mth-0175-study.json`](../data/research-review/mth-0175-study.json)
  (MTH-0175) supplies a blinded-study protocol with an empty/not-evaluated
  human result, while
  [`data/research-review/mth-0185-enriched-study.json`](../data/research-review/mth-0185-enriched-study.json)
  (MTH-0185) records deterministic assignment, evidence excerpts, locality,
  digests, and holdout isolation without generating reviewer labels.
- [`data/benchmark/mth-0195-independent-exploration.json`](../data/benchmark/mth-0195-independent-exploration.json)
  (MTH-0195) provides a later authored 24-task, four-domain benchmark surface
  with explicit evidence slices and disjoint partitions. It contains no model
  outputs, reviewer labels, empirical scores, or superiority comparison.

These observations support describing an inspectable **instrument and protocol
surface**. They do not yet support describing its effectiveness.

### Paper 1 allowed claims

- The checked-in research artifacts implement or specify explicit boundaries for
  evidence references, claim status, scope, locality, negative knowledge,
  holdouts, reproducibility metadata, and promotion state.
- The artifacts provide a concrete basis for asking reproducible exploration
  questions over bounded repository evidence.
- The benchmark and review surfaces separate discovery/protocol construction
  from later review and synthesis.
- The instrument is a candidate research method whose usefulness remains to be
  evaluated.

### Paper 1 explicitly excluded claims

- Not the first architecture knowledge, pattern, retrieval, benchmark, or
  evidence-management instrument.
- No claim that evidence-bounded exploration is better than web search, direct
  LLM generation, human review, or another baseline.
- No claim that a candidate relation, mathematical view, or composition is
  true, compatible, causal, deployable, or formally proved.
- No claim of human usability, reviewer agreement, model quality, statistical
  power, or generalization from protocol capacity.

### Paper 1 limitations

- MTH-0169, MTH-0172, and MTH-0174 are historical/not-present in the MTH-0201
  baseline; their outcomes cannot be recreated from this outline.
- MTH-0175 is a protocol, not completed human evidence. Human review remains
  optional/deferred.
- MTH-0195 is authored task capacity, not a sampled population or measured
  performance result.
- The instrument's schema and provenance discipline do not by themselves show
  that users find, understand, or correctly apply the resulting knowledge.

### Paper 1 next evidence

1. Preserve a versioned, reviewed task set and run the instrument under a
   pre-registered, evidence-local protocol.
2. If approved, optionally collect human review under MTH-0175 with explicit
   consent, reviewer scope, labels, and empty/not-evaluated handling. Do not
   infer a human result from the existing agent records.
3. Report retrieval, locality, abstention, scope, and claim-discipline outcomes
   separately before considering any synthesis or comparative statement.

## Paper 2 — evidence locality, abstention, and candidate-quality observations

### Paper 2 working title

**Evidence Locality and Abstention in Bounded Architecture Exploration:
Provisional Agent-Only Observations**

### Paper 2 research question

When an architecture-exploration task supplies bounded evidence, what can be
observed about evidence support, candidate locality, scope, claim discipline,
abstention, counterexample awareness, and related error dimensions without
collapsing them into a single quality score?

### Paper 2 current findings (provisional)

- MTH-0172 defines the candidate-quality lineage, but its historical result is
  not present in the current indexed baseline:
  `data/benchmark/mth-0172-candidate-quality.json` (MTH-0172; status recorded
  in MTH-0201). No metric is reconstructed.
- MTH-0174 and MTH-0195 define bounded cross-system task surfaces, but task
  count and protocol partitions are not empirical quality observations:
  `data/benchmark/mth-0174-cross-system.json` (MTH-0174, historical/not
  present) and
  [`data/benchmark/mth-0195-independent-exploration.json`](../data/benchmark/mth-0195-independent-exploration.json)
  (MTH-0195).
- MTH-0185 makes candidate/evidence locality, claim type, source identity,
  scope, negative knowledge, and holdout isolation explicit in
  [`data/research-review/mth-0185-enriched-study.json`](../data/research-review/mth-0185-enriched-study.json).
- MTH-0186 and MTH-0187 contain bounded **agent-only, non-human** pilot
  observations over the enriched packet:
  [`data/research-review/pilots/mth-0186.json`](../data/research-review/pilots/mth-0186.json)
  and
  [`data/research-review/pilots/mth-0187.json`](../data/research-review/pilots/mth-0187.json).
  Their payload-handling observations are not human review, conversational
  reasoning time, or reviewer productivity.
- MTH-0188 reports separate agent-only dimensions (including evidence support,
  claim type, scope, false links, usefulness, counterexamples, abstention, and
  effort) in
  [`data/research-review/scoring/mth-0188-agent-review-scoring.json`](../data/research-review/scoring/mth-0188-agent-review-scoring.json).
  MTH-0196 is represented by this scoring artifact together with
  [`data/benchmark/mth-0177-statistical-analysis.json`](../data/benchmark/mth-0177-statistical-analysis.json),
  not by a separate result file.
- MTH-0193 repeats the bounded **agent-only, non-human** observation surface in
  [`data/research-review/pilots/mth-0193.json`](../data/research-review/pilots/mth-0193.json),
  with two runs and 32 bounded observations as described by the companion
  artifact documentation. MTH-0177/MTH-0196 preserve separate dimensions,
  exact intervals where denominators exist, small-sample warnings, and an
  explicitly empty/not-evaluated human stratum.
- MTH-0175 remains a protocol with no completed human labels:
  [`data/research-review/mth-0175-study.json`](../data/research-review/mth-0175-study.json).
  MTH-0176's direct-LLM control contract and MTH-0194's readiness record both
  leave direct-LLM **not evaluated**:
  `data/benchmark/mth-0176-direct-llm-control.json` (MTH-0176, absent manifest
  in MTH-0201) and
  [`data/analyses/mth-0194-direct-llm-readiness.json`](../data/analyses/mth-0194-direct-llm-readiness.json)
  (MTH-0194).

The current evidence therefore supports a descriptive account of separate,
agent-only observation dimensions and abstention/uncertainty handling. It does
not support a general candidate-quality estimate.

### Paper 2 allowed claims

- The research artifacts preserve evidence-local and scope-sensitive dimensions
  rather than silently converting missing or unknown evidence into support.
- Agent-only pilots produced bounded observations under the declared packet and
  task contracts; their labels and timing are descriptive observations of those
  runs.
- The scoring/statistical artifacts keep agent and human strata separate,
  retain null/not-evaluated states, and avoid an aggregate quality score.
- The protocol makes abstention, false links, scope loss, claim discipline, and
  counterexample handling available as distinct questions for future study.

### Paper 2 explicitly excluded claims

- Agent-only observations are not human findings, human agreement, human
  productivity, or a proxy for human review.
- No claim that the observed agent labels measure general model quality,
  reliability, intelligence, or reasoning ability.
- No aggregate quality ranking, causal explanation, superiority claim, or
  population-level error rate beyond the declared bounded observations.
- No direct-LLM baseline or comparison: direct-LLM remains not evaluated.
- No inference from unobserved MTH-0195 tasks, holdouts, empty denominators, or
  the empty human stratum.

### Paper 2 limitations

- The agent pilots are non-human observations over a fixed enriched packet, not
  independent human replications or a representative sample.
- Small denominators receive warnings and do not justify broad rates;
  protocol capacity is not statistical power.
- Timing covers the stated bounded payload-handling scope, not conversational
  reasoning or productivity.
- MTH-0172 and MTH-0174 historical results are not present in MTH-0201; only
  their recorded boundaries can be cited.
- The MTH-0175 human stratum is empty/not-evaluated. Human review is optional
  and deferred, not silently supplied by agents.

### Paper 2 next evidence

1. Keep any future agent replication separately identified by run, packet,
   source digest, and evidence slice; do not merge it into a human stratum.
2. Optionally execute the MTH-0175 human protocol after explicit review of its
   consent, sampling, labeling, and privacy procedures.
3. Evaluate a direct-LLM condition only with exact provider/model/runtime,
   prompt and input digests, secret-safe output provenance, and the same
   evidence-local task contract. Until then, report **not evaluated**.
4. Predefine how abstention, unknown, unsupported, and counterexample outcomes
   are reported without imputing missing labels.

## Paper 3 — bounded cross-system microstructure and SQLite case studies

### Paper 3 working title

**From Cross-System Microstructures to Bounded Experiments: Architecture Views
with SQLite Case Studies**

### Paper 3 research question

Can small cross-system feature/relation views and bounded operational case
studies remain inspectable, evidence-linked, and appropriately limited when a
candidate mathematical view or experiment is used to compare systems?

### Paper 3 current findings (provisional)

- MTH-0174 is the historical cross-system task-set lineage, but its artifact
  `data/benchmark/mth-0174-cross-system.json` is not present in the MTH-0201
  baseline. MTH-0178's historical SQLite WAL/savepoint composition prototype
  is also indexed as not present, including
  `data/experiments/g6-sqlite-composition-mth-0178-results.json` and
  `data/mathviews/sqlite-wal-savepoint-composition-mth-0178.json` (MTH-0178).
  Neither historical surface should be presented as a current experiment.
- MTH-0195 supplies a current bounded cross-system task/evidence surface over
  four domains in
  [`data/benchmark/mth-0195-independent-exploration.json`](../data/benchmark/mth-0195-independent-exploration.json).
  Its composition tasks are proposed, non-canonical, and unproven; they do not
  establish compatibility or a production recommendation.
- MTH-0197 records a bounded local SQLite two-writer lock-contention sequence
  across three repetitions in
  [`data/experiments/g5-sqlite-busy-timeout-results-mth-0197.json`](../data/experiments/g5-sqlite-busy-timeout-results-mth-0197.json),
  [`data/experiments/g5-sqlite-busy-timeout-observation-mth-0197.json`](../data/experiments/g5-sqlite-busy-timeout-observation-mth-0197.json),
  and the candidate view
  [`data/mathviews/sqlite-busy-timeout-mth-0197.json`](../data/mathviews/sqlite-busy-timeout-mth-0197.json).
  The bounded observation includes lock failure under the scripted sequence,
  post-release commit/reopen, and integrity checks; timing is null/not
  measured.
- MTH-0198 and MTH-0202 provide bounded browser-surface observations rather
  than system-wide performance evidence:
  [`docs/mth-0198-graph-browser-audit.md`](../docs/mth-0198-graph-browser-audit.md)
  (MTH-0198) records local Chromium and Lighthouse smoke checks, while
  [`docs/mth-0202-browser-readiness.md`](../docs/mth-0202-browser-readiness.md)
  (MTH-0202) records fixture-backed browser readiness and explicitly leaves
  real API/D1, Firefox, device, network, and interactive edge/path gaps
  unmeasured.
- MTH-0201 provides the reproducibility index and records the absent historical
  MTH-0178 surface, present MTH-0197 surface, and present MTH-0198 surface:
  [`data/reproducibility/mth-0201-reproducibility-index.json`](../data/reproducibility/mth-0201-reproducibility-index.json).

These artifacts support case-study language about inspectable, bounded
observations and candidate views. They do not support a general SQLite model,
a proven composition, or a cross-system performance result.

### Paper 3 allowed claims

- A cross-system benchmark can state task, evidence, source, scope, and
  candidate boundaries explicitly.
- MTH-0197 is a reproducible-looking, fixed-environment observation of one
  scripted local SQLite lock sequence, with its review and canonical boundaries
  retained.
- A mathematical view can serve as a candidate representation of declared
  states and transitions when its assumptions and evidence are visible.
- MTH-0198 and MTH-0202 can be cited as bounded local/fixture browser smoke
  observations with explicit unmeasured gaps.

### Paper 3 explicitly excluded claims

- No proof that MTH-0197's candidate state machine describes all SQLite
  concurrency, timeout, durability, crash-recovery, checkpoint, or deployment
  behavior.
- No claim of SQLite compatibility, performance, architecture superiority, or
  causality outside the fixed two-writer local sequence.
- No claim that MTH-0195 composition candidates work, are safe, or are ready
  for production.
- No claim that local Lighthouse, desktop Chromium, fixture, or small-viewport
  values represent real mobile devices, networks, deployed systems, or all
  browsers.
- No current MTH-0178 result: the historical prototype is absent from the
  indexed baseline.

### Paper 3 limitations

- MTH-0197 uses one source/build context, SQLite defaults, two local writers,
  zero busy timeout, and three repetitions; timing was deliberately not
  measured.
- The optional math view is a candidate consistency record, not a formal proof
  or canonical card.
- MTH-0195 task partitions and candidate prompts do not establish empirical
  cross-system validity.
- MTH-0198's browser audit and MTH-0202's fixture readiness audit leave
  real-device, network, Firefox attachment, edge targeting, and some API/D1
  paths unmeasured.
- Human review remains optional/deferred, and direct-LLM remains not evaluated.

### Paper 3 next evidence

1. Review each candidate view against its local evidence and assumptions before
   any promotion; retain rejected or unsupported relations as negative
   knowledge.
2. Repeat SQLite observations only as separately identified experiments across
   declared timeout, journal, writer, crash, and deployment conditions; do not
   overwrite MTH-0197 silently.
3. Extend cross-system tasks with reviewed evidence and optional human review,
   while preserving candidate/proof and discovery/synthesis boundaries.
4. Close browser gaps only with named environments and reproducible fixtures;
   report null/not-measured results rather than substituting local smoke values.

## Future comparative evaluation (deferred)

Human-versus-agent and direct-LLM comparative evaluation is a future study, not
one of the three current papers. Human review is optional and deferred under
the MTH-0175 protocol. The MTH-0186/MTH-0187/MTH-0193 records remain
agent-only and non-human. MTH-0176, MTH-0194, and MTH-0195 leave direct-LLM
**not evaluated**; no direct-LLM output, provider/model comparison, or baseline
score is available.

Any future comparison must predeclare the task set, evidence slices, human
review protocol, direct-LLM provenance, abstention and missingness policy,
scoring dimensions, uncertainty treatment, and promotion boundary. It must not
turn an empty human stratum into a zero, treat cache/readiness as inference, or
use agent-only observations as human evidence.

## Compact evidence index

The table is a navigation aid, not a replacement for the artifacts. “Absent”
means MTH-0201 records the path as not present in the indexed baseline; it does
not mean the historical work never existed.

| ID | Exact artifact path(s) | Current role/status |
| --- | --- | --- |
| MTH-0169 | `data/benchmark/mth-0169-exploration.json` | Historical exploration fixture; absent in MTH-0201, no result claimed. |
| MTH-0172 | `data/benchmark/mth-0172-candidate-quality.json` | Historical candidate-quality result; absent in MTH-0201, no metric reconstructed. |
| MTH-0174 | `data/benchmark/mth-0174-cross-system.json` | Historical cross-system task set; absent in MTH-0201, capacity is not a result. |
| MTH-0175 | `data/research-review/mth-0175-study.json` | Blinded review protocol; human labels empty/not evaluated. |
| MTH-0176 | `data/benchmark/mth-0176-direct-llm-control.json` | Direct-LLM control contract; manifest absent in MTH-0201, direct-LLM not evaluated. |
| MTH-0177 | `data/benchmark/mth-0177-statistical-analysis.json` | Statistical reporting over bounded observations; agent-only and provisional. |
| MTH-0178 | `data/experiments/g6-sqlite-composition-mth-0178-results.json`; `data/mathviews/sqlite-wal-savepoint-composition-mth-0178.json` | Historical SQLite composition prototype; absent in MTH-0201. |
| MTH-0185 | `data/research-review/mth-0185-enriched-study.json` | Enriched packet and evidence-locality contract; no reviewer result. |
| MTH-0186 | `data/research-review/pilots/mth-0186.json` | Agent-only, non-human packet-A observations. |
| MTH-0187 | `data/research-review/pilots/mth-0187.json` | Agent-only, non-human packet-B observations. |
| MTH-0188 | `data/research-review/scoring/mth-0188-agent-review-scoring.json` | Agent-only dimension scoring; no aggregate quality claim. |
| MTH-0193 | `data/research-review/pilots/mth-0193.json` | Repeated agent-only, non-human observations. |
| MTH-0194 | `data/analyses/mth-0194-direct-llm-readiness.json` | Secret-safe local readiness; direct-LLM not evaluated. |
| MTH-0195 | `data/benchmark/mth-0195-independent-exploration.json` | 24-task cross-system benchmark surface; no outputs or scores. |
| MTH-0196 | `data/benchmark/mth-0177-statistical-analysis.json`; `data/research-review/scoring/mth-0188-agent-review-scoring.json` | Represented aggregation release; observed strata kept separate. |
| MTH-0197 | `data/experiments/g5-sqlite-busy-timeout-results-mth-0197.json`; `data/experiments/g5-sqlite-busy-timeout-observation-mth-0197.json`; `data/mathviews/sqlite-busy-timeout-mth-0197.json` | Bounded SQLite observation and candidate view; under review, non-canonical. |
| MTH-0198 | `docs/mth-0198-graph-browser-audit.md` | Local browser/Lighthouse smoke audit; not representative deployment metrics. |
| MTH-0201 | `data/reproducibility/mth-0201-reproducibility-index.json` | Reproducibility index and source/status boundary for the evidence wave. |
| MTH-0202 | `docs/mth-0202-browser-readiness.md` | Fixture browser-readiness record; real API/device/network gaps remain. |

## Writing order and status

1. **MTH-0205 planning artifact — complete:** preserve `paper/README.md`, add
   this bounded outline, and keep all findings provisional.
2. **Paper 1 — outline ready, manuscript deferred:** write the instrument and
   boundary description first; do not write effectiveness or novelty claims.
3. **Paper 2 — outline ready, evidence synthesis deferred:** write the separate
   locality/abstention/observation dimensions only after checking artifact
   digests and keeping agent-only and human strata distinct.
4. **Paper 3 — outline ready, case-study manuscript deferred:** write the
   cross-system/SQLite cases with explicit assumptions and exclusions; do not
   promote candidate views to proofs.
5. **Comparative evaluation — deferred:** human review is optional/deferred;
   direct-LLM remains not evaluated. No comparative paper is currently ready.

No paper正文, LaTeX, BibTeX, figure, author metadata, arXiv submission
tooling, deployment, or non-`paper/` file is part of this task.
