# MTH-0118: synthesis validation and architecture novelty benchmark

Status: planning/design artifact only. This document specifies an evaluation
plan; it reports no experiment results and changes no canonical card, draft,
schema, API, MCP, or production behavior.

## 1. Purpose and research boundary

The benchmark evaluates the proposed loop from source evidence to
microstructure to mathematical view or typed composition to a candidate macro
architecture and, where possible, a prototype or experiment:

```text
fixed evidence bundle
  -> evidence-linked microstructures
  -> bounded mathematical views and/or typed composition candidates
  -> candidate synthesis with interfaces, constraints, properties, failures
  -> review, falsification, prototype or experiment
  -> accepted, rejected, or still-undetermined candidate
```

The benchmark is intended to answer whether explicit structure improves
*validated candidate quality and review usefulness* over less structured
retrieval or direct generation. It must not be used to claim that a coherent
answer is a correct architecture, that a finite contract check proves an
implementation, or that a novel graph position establishes historical
influence.

This plan follows the current contracts:

- `docs/microstructure-ontology.md`: scale-aware units with state, events,
  operations, boundaries, resources, failures, scope, and local evidence;
- `docs/mathematical-view-contracts.md`: finite, checkable candidate models
  classified as `valid`, `invalid`, or `undetermined`, not proofs;
- `docs/temporal-composition-contract.md`: typed requirements, provisions,
  adapters, boundaries, property effects, preconditions, postconditions,
  conflicts, counterexamples, uncertainty, and `proven: false`;
- `docs/negative-knowledge-contract.md`: bounded counterexamples and failed
  hypotheses whose scope cannot be generalized into universal claims;
- `docs/cross-domain-analogies.md`: analogy mappings with non-equivalence,
  non-preserved properties, scope, and counterexamples;
- `docs/llm-modeling.md`: fixed provenance, evidence-local citations,
  separated breadth/citation/error/usefulness measures, and human promotion.

Every candidate result produced during evaluation remains a candidate with
`proven: false` (for typed compositions), `claim_status: proposed` or
`under-review`, and one of `fact`, `inference`, `hypothesis`, or `analogy` for
each claim. A benchmark pass is evidence about a workflow under a declared
scope; it is not permission to promote a candidate to `data/systems/`.

### 1.1 Claims the benchmark may test

The following are hypotheses, not current facts:

| ID | Claim type | Hypothesis to test |
| --- | --- | --- |
| H1 | hypothesis | Explicit microstructures improve recall of useful cross-community candidates over product-name and feature-text retrieval at a fixed review budget. |
| H2 | hypothesis | Typed composition exposes interface conflicts and weakened properties earlier than untyped similarity or direct LLM synthesis. |
| H3 | hypothesis | Mathematical-view checks reject more attractive but invalid candidates than reviewer intuition alone, while leaving incomplete observations `undetermined`. |
| H4 | hypothesis | Negative knowledge and held-out counterexamples reduce repeated false links and unsupported property transfers. |
| H5 | hypothesis | Evidence-bounded LLM prompting improves citation locality, claim-type discipline, and coverage without hiding uncertainty. |
| H6 | hypothesis | Structured candidates can reduce expert review time while preserving or improving error detection. |
| H7 | hypothesis | Some candidates are novel in one or more architecture dimensions, but novelty is dimension-specific and does not imply usefulness, correctness, or historical influence. |

No hypothesis is accepted merely because a candidate is distant in a graph,
semantically similar, fluent, or classified `valid` by a finite mathematical
check.

## 2. Evaluation units and end-to-end protocol

An evaluation unit is a tuple:

```text
(evidence bundle, frozen source revision, task/question, method, candidate set,
 reviewer judgments, validation outcomes, optional prototype/experiment)
```

The unit must retain a run manifest containing at least:

- protocol version and benchmark version;
- source repository IDs and immutable commits or archive digests;
- system, feature, view, microstructure, composition, analogy, and negative
  knowledge IDs used as inputs;
- method and baseline name;
- provider, exact model identifier, prompt digest, input-bundle digest, and
  deterministic-inspector provenance for LLM runs;
- deployment origin, version, conditions, exclusions, and workload where
  applicable;
- random seed and decoding parameters where applicable;
- candidate IDs, evidence IDs, claim types/statuses, and validation logs;
- reviewer pool, rubric version, blinded assignment, and adjudication record;
- outcome (`accepted`, `rejected`, `undetermined`, `falsified`, or
  `not-evaluated`) with a reason.

The run manifest is an audit record, not evidence by itself. Evidence must be
linked from the source bundle or an explicitly produced experiment. A URI or
citation that was not available to the run cannot be counted as run-local
support.

### 2.1 Staged protocol

1. **Freeze and partition evidence.** Create a dated, immutable bundle at
   fixed commits. Split by repository/system and, for temporal tests, by
   release or historical interval. Do not put a later reviewer judgment,
   generated candidate, or target-system answer in the input partition.
2. **Construct task cards.** Each task states the question, requested
   dimensions, allowed scope, excluded claims, expected deliverable, and
   stopping conditions. Tasks must include positive examples and deliberately
   tempting boundary cases where feasible.
3. **Run discovery methods.** Execute each baseline and the structured method
   against the same evidence budget. Record all candidates, not only the ones
   later judged useful, to measure false-link and selection effects.
4. **Normalize candidate records.** Map output into the existing vocabulary.
   Unsupported statements become unknown or are removed from the supported
   view; they must not be silently promoted to `fact`. Analogy is retained as
   `analogy`, and candidate composition retains `proven: false`.
5. **Run deterministic checks.** Validate local references and evidence IDs;
   run mathematical checks; check typed obligations, adapters, boundaries,
   conflicts, scope, and required counterexamples. A failed check is
   `invalid`; missing observations are `undetermined`; neither is a proof of
   a broad negative claim.
6. **Adversarially falsify.** Replay known negative-knowledge records, held-out
   counterexamples, scope changes, version changes, deployment changes, and
   resource/failure perturbations. Record which claim was falsified and the
   smallest scope in which the failure occurs.
7. **Review blind to method.** Independent reviewers judge evidence support,
   interface compatibility, property effects, novelty dimensions, and
   usefulness. Adjudicate disagreements without deleting the original labels.
8. **Prototype or experiment selectively.** Only candidates that pass the
   preceding review and have an executable question enter a prototype. The
   experiment must declare workload, environment, metrics, failure oracle,
   and validity scope before execution.
9. **Report by dimension.** Report distributions and confidence intervals for
   each metric and baseline. Do not collapse all outcomes into a confidence or
   novelty score.

## 3. Dataset design

The dataset should be released as manifests and immutable evidence bundles,
not as an unreviewed collection of newly canonicalized cards.

### 3.1 Required dataset slices

| Slice | Contents | Labels or annotations | Leakage control |
| --- | --- | --- | --- |
| Reviewed architecture corpus | Reviewed cards, typed relations, temporal contexts, evidence, versions, and deployment scopes | Evidence-supported features, views, relations, claim types/statuses | Repository/system-level split; no evidence from the target revision in prompts |
| Microstructure corpus | Reviewed or independently audited primitive/mechanism/subsystem/system units | State/events, operations, I/O, pre/postconditions, invariants, boundaries, resources, failures, scope | Split by source system and concept family; preserve partiality labels |
| Mathematical-view set | Candidate graph, DAG, order, state-machine, simulation, cost, queueing, reliability, and other supported families | Expected check outcomes and reasons; `valid`, `invalid`, or `undetermined` | Keep invalid and incomplete cases in held-out sets; do not infer labels from prose alone |
| Composition set | Typed components, explicit adapters/boundaries, property effects, preconditions, postconditions, conflicts, examples, counterexamples, uncertainties, disagreements | Compatibility, conflict, preservation, and review outcome | Hold out component pairs and cross-community paths, not only random rows |
| Negative-knowledge set | Invalid compositions, misleading similarities, scope violations, failed hypotheses, falsified experiments, retractions, supersessions | Bounded claim, counterexample, implication, scope, replacement/lifecycle links | Keep adversarial examples and their source evidence out of candidate generation |
| Analogy set | Cross-domain mappings | Correspondences, shared/preserved/non-preserved properties, non-equivalence, substitutability, counterexamples | Domain-pair and time split; historical influence labels require direct evidence |
| Historical/temporal set | Multiple versions or dated evidence for the same system or relation | What changed, when, and what is directly evidenced | Train/evaluate in chronological order; prohibit future evidence in past tasks |
| Deployment/experiment set | Reproducible prototypes, workloads, configurations, traces, and failures | Runtime behavior, resource effects, deployment-specific outcomes | Environment, configuration, and workload held out where possible |
| Reviewer set | Task/candidate packets and independent expert judgments | Correctness/support, usefulness, time, confidence, disagreement, missed error | Blind method and randomized packet order |

The repository inventory is a candidate source for the corpus, not an asserted
benchmark count. Before any run, record exact counts, missing fields, duplicate
evidence, and inter-annotator agreement. If a slice is too small for a reliable
split, report it as exploratory rather than manufacturing a statistical claim.

### 3.2 Gold labels and annotation policy

Gold does not mean metaphysical truth. A gold record is a reviewed reference
under a stated evidence and scope boundary. At least two reviewers should
label high-impact claims independently, with a third adjudicator for
disagreement. Record:

- direct source support and exact evidence IDs;
- whether the statement is a `fact`, `inference`, `hypothesis`, or `analogy`;
- review status and whether support is local to the claim;
- scope (system, version, deployment origin, conditions, exclusions);
- preserved, weakened, conflicting, unverified, and non-preserved properties;
- known counterexamples and the implication of each;
- whether the label is supported by source evidence, a deterministic check, an
  experiment, or reviewer judgment.

An annotation must not upgrade a resemblance to `uses`, `composes`,
`influenced-by`, equivalence, substitutability, or a proof. Historical claims
need direct historical evidence; temporal co-occurrence is not influence.

## 4. Baselines and ablations

All methods receive the same task, evidence budget, time budget (where
applicable), and output cutoff. Report both recall-oriented and precision-
oriented settings.

1. **Lexical baseline:** product-name, keyword, and feature-text retrieval
   followed by a fixed reviewer rubric. This measures the cost of terminology
   matching and familiar templates.
2. **Vector baseline:** embedding nearest neighbors with no typed relation
   inference. Similarity is recorded as a discovery signal only.
3. **Graph baseline:** existing typed relation paths, community/bridge
   candidates, and centrality/path heuristics. Graph position is not truth.
4. **Vector-plus-graph baseline:** union or reranking of the preceding
   candidates, with no microstructure contract.
5. **Direct LLM baseline:** the same model and evidence bundle asked for a
   design or comparison without structured microstructure, contract, or
   counterexample instructions. Its output remains a draft and is scored for
   unsupported claims.
6. **Structured retrieval baseline:** microstructure and mathematical-view
   retrieval without LLM synthesis. This isolates representation benefits.
7. **Full evidence-bounded method:** human question, graph/vector discovery,
   LLM explanation, evidence-linked microstructure, deterministic checks,
   typed composition, negative knowledge, review, and selective experiment.
8. **Ablations:** remove one of microstructures, mathematical checks, typed
   obligations, negative knowledge, analogy boundaries, or reviewer-visible
   provenance at a time. Do not interpret an ablation as an independent
   architecture method; it isolates workflow contributions.
9. **Human reference:** expert search and synthesis under the same evidence
   and time budget. This is a reference condition, not an assumption of human
   perfection.

The structured method must never be credited for a deterministic check or
evidence record that was also supplied as a hidden answer to a baseline.

## 5. Metrics

Use per-task, macro-averaged metrics as the primary report; provide
micro-averages and system/bootstrap confidence intervals as secondary views.
Report denominators, abstentions, and `undetermined` results explicitly.

### 5.1 Evidence and claim discipline

- **Evidence recall:** supported reference claims cited by the candidate / all
  supported reference claims requested by the task.
- **Citation precision:** cited evidence items judged to support the claim /
  all cited evidence items. A URI existing is not enough; the content must
  support the statement.
- **Citation locality:** fraction of claims whose evidence IDs are present in
  the supplied bundle and attached to that claim or its containing contract.
- **Unsupported claim rate:** claims with no adequate support / all factual or
  inferential claims. Report analogy and hypothesis separately.
- **Claim-type accuracy:** agreement with reviewed type (`fact`, `inference`,
  `hypothesis`, `analogy`), with a confusion matrix.
- **Scope completeness:** required systems, versions, deployment origins,
  conditions, and exclusions recorded / required scope fields.
- **Boundary omission rate:** required non-preserved properties, exclusions,
  uncertainty, disagreement, or failure modes omitted / those identified by
  reviewers.
- **Provenance completeness:** required protocol fields present and digest-
  consistent / required fields.

### 5.2 Breadth, retrieval, and bridge quality

- **Task breadth recall:** requested dimensions or concept families covered by
  at least one reviewable candidate / requested dimensions.
- **Cross-community breadth:** distinct source-target community pairs covered,
  reported alongside same-community coverage so distant links cannot hide
  missing basics.
- **Useful bridge recall/precision:** reviewed useful bridge candidates found /
  all useful references, and useful candidates / all proposed bridges.
- **False-link rate:** proposed links rejected as unsupported, incompatible,
  scope-violating, or misleading / all proposed links.
- **Novel candidate diversity:** distinct evidence-supported candidate families
  after clustering by canonical structure, not wording. Report cluster
  procedure and sensitivity; diversity is not usefulness.
- **Graph/vector complementarity:** candidates found by one route but not the
  other, stratified by eventual review outcome. Disagreement is a result to
  inspect, not an error by itself.

### 5.3 Microstructure and mathematical validation

- **Microstructure field completeness:** populated and evidence-supported
  dimensions (state/events, operations, I/O, pre/postconditions, invariants,
  boundaries, resources, failures, scope) / dimensions required by the task.
- **Reference closure rate:** valid IDs and local evidence references / all
  references.
- **Mathematical classification accuracy:** agreement with reviewed finite
  check outcomes for `valid`, `invalid`, and `undetermined`.
- **Invalid rejection rate:** known invalid models classified `invalid` /
  known invalid models presented.
- **Underdetermination discipline:** incomplete or uncheckable models left
  `undetermined` / incomplete models. A false `valid` is a high-severity error.
- **Check explanation adequacy:** deterministic reason and individual check
  results judged sufficient to reproduce the classification.

These metrics evaluate the supplied model and finite data. They do not measure
whether the source implementation has the modeled semantics unless an
independent experiment does so.

### 5.4 Typed composition and synthesis validation

- **Obligation satisfaction:** `requires` obligations matched by explicit
  `provides` or declared adapters under the candidate scope / all requirements.
- **Adapter precision:** accepted adapters that are independently supported /
  all proposed adapters. Adapters must not be inferred from names or graph
  proximity.
- **Conflict precision/recall:** correctly identified typed conflicts against
  reviewer or experiment labels. Include resource, boundary, lifecycle,
  version, and property conflicts.
- **Property preservation precision:** properties labeled `preserves` or
  `strengthens` and supported by evidence/experiment / all such labels.
- **Weakening detection recall:** known weakened or non-preserved properties
  surfaced / all known weakenings.
- **Unverified-property honesty:** unsupported transfers labeled `unverified`
  rather than accepted as preserved.
- **Pre/postcondition coverage:** composition conditions with evidence and
  executable or reviewable checks / required conditions.
- **Counterexample recall:** known counterexamples discovered or cited /
  counterexamples in the held-out reference set.
- **Candidate survival:** candidates surviving each stage, reported as a
  funnel, not as a success percentage without denominators.
- **Prototype predictive value:** among candidates admitted to an experiment,
  the fraction whose declared behavioral prediction is supported within scope;
  report falsifications equally and do not discard failed candidates.

`proven: false` remains unchanged for every candidate, including one that
passes typed checks or an experiment. An experiment can support a bounded
claim and still leave broader properties `hypothesis` or `undetermined`.

### 5.5 LLM-specific breadth and citation measures

Run at least multiple seeds or repeated calls when cost permits, and report
variance rather than a single favorable completion.

- requested-coverage breadth and cross-community breadth;
- evidence citation precision, recall, and locality;
- unsupported, hallucinated, and evidence-misquoted claim rates;
- claim-type and scope classification accuracy;
- counterexample and negative-knowledge recall;
- disagreement preservation rate (conflicts retained rather than silently
  resolved);
- duplicate/template rate, measured against canonical structural clusters;
- abstention and `undetermined` rate;
- token, latency, and evidence-budget cost;
- reviewer usefulness conditioned on output length and candidate count.

Do not reward citations merely for being numerous. A long answer with many
irrelevant citations can score lower than a short answer with complete local
support.

### 5.6 Reviewer usefulness

Use a randomized, blinded review study with a pre-registered rubric. Primary
measures are:

- median active review time per accepted/rejected/undetermined candidate;
- error detection recall and false acceptance rate;
- correction burden (number and severity of edits before a safe review
  decision);
- reviewer confidence calibration, separated from correctness;
- evidence navigation actions or time to verify a citation;
- agreement and adjudication rate;
- task completion and ability to state remaining uncertainty;
- perceived usefulness and cognitive load, reported as secondary ordinal
  measures;
- review throughput at a fixed error ceiling.

The workflow is useful only if review time falls without increasing missed
unsupported claims, scope violations, or false acceptance. A reviewer who
accepts a fluent but unsupported candidate is not a usefulness success.

## 6. Architecture novelty benchmark

Novelty is evaluated against a declared reference window and representation,
not against wording or model surprise. Each dimension gets a separate
binary/ordinal review label and an evidence trail. A candidate may be novel in
one dimension and ordinary in another; all novelty labels are hypotheses until
review and, where applicable, experiment. No aggregate novelty score is a
release gate.

### 6.1 Dimensions and operational tests

| Dimension | Candidate signal | Required comparison | Main falsifier and boundary |
| --- | --- | --- | --- |
| Topology | New typed arrangement of components, boundaries, or state/event paths | Canonical structure graph and graph-isomorphic/canonicalized reference set under the same abstraction level | Renaming, reordering, extra wrapper, or graph projection artifact; topology novelty does not establish usefulness |
| Composition | New combination of independently known microstructures with explicit interfaces/adapters | All admissible pair/multi-component compositions in the reference window and reviewer-confirmed prior designs | Hidden prior art, unsupported adapter, or an untyped similarity edge; `proven` remains false |
| Constraints | New conjunction or trade-off of preconditions, invariants, resource limits, or failure containment | Constraint signatures and reviewed design/problem corpus at the same scope | Restating familiar constraints, changing units, or omitting a required condition |
| Behavior | New externally observable transition, property effect, failure/recovery behavior, or workload trade-off | Behavior traces/contracts under identical workload, version, and deployment scope | Unmeasured behavior, finite-view artifact, or a claim that only changes implementation detail |
| Deployment | New placement, isolation, data/control boundary, or operational topology under a declared environment | Deployment/configuration reference set and reproducible environment comparison | Configuration-only variation without architectural effect, or transfer outside declared origin |
| Historical | New directly evidenced relation about chronology, influence, adoption, or independent emergence | Dated primary sources, release history, design records, and explicit provenance | Co-occurrence, textual similarity, or retrospective resemblance; analogy cannot become influence without direct evidence |

### 6.2 Novelty scoring and review record

The planned record for each dimension should include:

```text
dimension
candidate_claim_id
reference_window
representation_and_normalization
nearest_prior_candidates
distance_or_difference_description
evidence_ids
claim_type: hypothesis | inference | analogy
claim_status: proposed | under-review | accepted | rejected
proven: false (when carried by typed composition)
falsifiers
reviewer_decision
```

Distances may be useful for triage, but a numeric distance is not a novelty
proof. Reviewers must explain the structural difference and identify the
nearest prior art. Report novelty precision at top-k only after independent
review; report coverage of known novel references separately. Leave the label
`undetermined` when the reference window or representation is incomplete.

Novelty must be stratified by source community, system scale, version, and
deployment origin. Otherwise a candidate can appear novel solely because its
community, vocabulary, or abstraction level is underrepresented.

## 7. Falsification and counterexample handling

Falsification is a first-class result, not an error to remove from the dataset.

1. **Before generation:** reserve negative-knowledge records and adversarial
   tasks. Do not disclose their exact wording to candidate generators.
2. **During normalization:** reject universal language and require bounded
   scope. A negative record must have `bounded: true`, at least one
   counterexample, local evidence, and an implication stating what cannot be
   claimed.
3. **During deterministic checking:** a failed law is `invalid`; absent data
   is `undetermined`; a passing finite check is not implementation proof.
4. **During composition review:** test missing providers, incompatible types,
   adapter removal, version mismatch, boundary crossing, resource exhaustion,
   lifecycle ordering, and failure/recovery paths.
5. **During experiments:** predeclare a failure oracle and record raw traces,
   configuration, workload, and environment digest. A negative result gets a
   new bounded negative-knowledge record or a review-linked experiment result;
   it is never generalized beyond its scope.
6. **After falsification:** retain the original candidate and link the
   counterexample, failed hypothesis, retraction, or supersession. Re-run only
   with an explicit changed scope or claim, preserving the lineage.

Required negative outcomes include:

- false positive bridge or misleading similarity;
- invalid composition due to unsatisfied obligation or unsupported adapter;
- property claimed as preserved but observed weakened or absent;
- mathematical law failure;
- deployment/version scope violation;
- unsupported historical influence claim;
- citation that exists but does not entail the cited statement;
- reviewer acceptance of a candidate later falsified by an available
  counterexample.

Counterexample discovery rate must be reported separately from candidate
precision. A method can have high precision by proposing very little and still
have poor ability to find dangerous failure cases.

## 8. Validity boundaries and limitations

- **Corpus bias:** reviewed cards and available repositories overrepresent
  accessible, documented systems and current vocabulary. Results do not
  generalize to undocumented systems without a new evidence study.
- **Reference incompleteness:** novelty is relative to the frozen reference
  window. “Not found” is not “never existed.”
- **Annotation subjectivity:** reviewer labels are bounded judgments. Publish
  rubric, disagreement, adjudication, and confidence intervals.
- **Evidence quality:** source code, official documents, papers, experiments,
  and secondary sources have different authority and granularity. Do not
  treat all evidence kinds as interchangeable.
- **Abstraction loss:** a microstructure or mathematical view is a partial
  representation. It can omit timing, security, economics, organizational
  behavior, or deployment details that determine real compatibility.
- **Finite checking:** a valid finite carrier, table, graph, or trace validates
  only the supplied model. Infinite or unobserved behavior remains outside
  the result.
- **Prototype external validity:** one workload, version, environment, or
  deployment origin does not establish all-runtime behavior.
- **LLM variance and contamination:** model version, prompt, context, and
  training overlap affect output. Pin provenance and test repeated runs.
- **Reviewer Hawthorne and learning effects:** repeated packets can reduce
  review time independently of the representation. Randomize order and use
  separate familiarization data.
- **Metric gaming:** maximizing citation count, graph density, breadth, or
  novelty can harm usefulness. Use separate metrics and an error ceiling.
- **Human baseline limitation:** experts are not an oracle and may have
  unequal domain knowledge. Record expertise and use multiple reviewers.
- **Historical claims:** chronology and influence require direct evidence;
  structural analogy and temporal adjacency are insufficient.
- **Security and operational risk:** a candidate must not be deployed merely
  because it passes the benchmark. Safety, privacy, and production readiness
  require separate review.

## 9. Proposed implementation sequence

This sequence is intentionally future work and should not be conflated with
the present design artifact.

1. Add a versioned benchmark manifest and frozen-bundle exporter that records
   source revisions, scope, evidence digests, and split membership.
2. Build an annotation guide and reviewer packet format for claim types,
   evidence locality, typed obligations, properties, counterexamples, and the
   six novelty dimensions.
3. Assemble a small pilot from existing reviewed cards, contract fixtures,
   negative-knowledge records, analogies, and independently reviewed
   microstructures. Record exact availability and missingness before scoring.
4. Implement baseline runners and a structured runner that only consumes
   explicit fields. Keep outputs in research/draft locations and retain
   `proven: false`.
5. Implement deterministic metric computation with denominators, abstention,
   `undetermined`, confidence intervals, and per-dimension reports.
6. Run held-out counterexample and scope-perturbation tests before any
   prototype experiment.
7. Run a blinded reviewer pilot and revise the rubric only through a versioned
   decision; do not silently relabel prior outcomes.
8. Add selective reproducible prototypes for candidates that pass the pilot,
   with predeclared behavior and failure oracles.
9. Publish negative results, rejected candidates, and limitations alongside
   any positive result. Promote nothing automatically to canonical cards.

### 9.1 Exit criteria for a future implementation

A future implementation is ready for a larger study only when it can:

- reproduce a run from its manifest and immutable evidence digests;
- distinguish `fact`, `inference`, `hypothesis`, and `analogy` in outputs;
- preserve evidence IDs and reject dangling or non-local references;
- keep typed composition candidates `proven: false`;
- produce `valid`, `invalid`, and `undetermined` mathematical outcomes with
  reasons and checks;
- retain uncertainty, disagreement, scope exclusions, and counterexamples;
- evaluate all baselines under matched evidence budgets;
- calculate the metrics above with visible denominators and split membership;
- record falsifications without broadening negative claims;
- keep novelty dimensions separate from correctness and historical influence;
- support blinded review and preserve raw reviewer/adjudication data;
- pass a red-team review for leakage, unsupported citations, and accidental
  canonical promotion.

## 10. Expected artifacts

The eventual study should produce, in separate research locations:

- versioned dataset and split manifests;
- reviewer guide, task packets, and adjudication records;
- method configuration and LLM protocol sidecars;
- candidate outputs and validation logs;
- metric tables with confidence intervals and error taxonomy;
- novelty comparison tables with reference windows and nearest prior art;
- prototype/experiment traces and bounded negative-knowledge records;
- a report that states results, non-results, falsifications, and limitations.

None of these artifacts should overwrite `data/systems/` or imply that a
benchmark result is a canonical Architecture Card. The benchmark's strongest
permitted conclusion is a scoped, evidence-backed statement about the tested
workflow, data, representation, model, reviewers, and conditions.
