# MTH-0147: decision on embeddings and Vectorize

**Status:** no production change; bounded lexical retrieval remains the deployed
baseline.

**Decision date:** 2026-10-26

## Decision

Do not add embeddings, Cloudflare Vectorize, a provider binding, a secret, a
migration, or a deployment in this task. The current corpus is large enough to
make an embedding experiment technically possible, but the evidence does not
establish that semantic retrieval is needed or that it would be safer or more
useful than the existing baseline.

The current reviewed corpus contains 219 cards, 830 features, 608 mathematical
views, 824 trade-offs, and 1,531 evidence records. The current retrieval builder
can expose 2,481 evidence-closed atomic documents. All 830 features and all 608
views have at least one locally resolvable evidence ID; the repository audit
reports zero missing evidence references. This supports a bounded research
comparison, not an automatic production index.

The limiting evidence is scope closure and evaluation coverage:

- `scope-context-corpus-audit-mth-0143.json` reports zero specified validity,
  workload, runtime-condition, scale, or failure-condition dimensions across
  the reviewed cards, and zero evidence scope metadata. Absence is explicitly
  not a negative finding, but it means scope-sensitive semantic ranking cannot
  be evaluated as if the corpus had complete scope metadata.
- The corpus has 818 fact and 12 inference features; mathematical views are
  445 inference, 160 hypothesis, 2 analogy, and 1 fact. Most feature/view
  statuses are omitted rather than explicitly reviewed (`823/830` and
  `604/608`). Claim types and status must remain visible and cannot be inferred
  from similarity.
- The repository contains the retrieval evaluation contract and a fixture, but
  no populated, independently reviewed lexical-versus-vector run. The fixture
  is not an experiment result. Therefore recall, nDCG, evidence locality,
  claim-type accuracy, scope completeness, false-link rate, abstention, and
  latency have no production decision evidence.

The no-change outcome is intentional: lexical ranking is explainable by token
overlap, runs without a provider data transfer or index cost, preserves the
existing fail-closed evidence hydration boundary, and is adequate for the
current bounded reviewed-card discovery use case. Similarity remains discovery
only. It must never create a relation or establish compatibility, causality,
historical influence, substitutability, originality, or truth.

## Options considered

| Option                                                         | Benefits                                                                                                                                                                                     | Costs and risks                                                                                                                                                                   | Decision                     |
| -------------------------------------------------------------- | -------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- | --------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- | ---------------------------- |
| Keep bounded lexical baseline                                  | Explainable score; no provider retention/training question; no embedding/index rebuild cost; D1 remains the source of truth; existing evidence closure and abstention behavior are exercised | Misses terminology and paraphrase matches; ranking is not semantic                                                                                                                | **Choose now**               |
| Offline/provider-neutral vectors with a local or CI fake index | Tests representation value without production data egress; preserves API contract; makes model, dimensions, metric, template, and source digests auditable                                   | Requires a fixed model and reproducible artifact; local model quality/privacy/cost still need evidence; no production latency evidence                                            | **Research gate only**       |
| Cloudflare Vectorize adapter                                   | Managed Worker query path, metadata filtering, and bounded top-K; likely operationally simpler than a bespoke service once a provider/model is selected                                      | Adds binding/resource lifecycle, rebuild publication, index cost, provider limits, metadata leakage/retention review, stale-index failure modes, and a second operational surface | **Only after gate**          |
| External managed vector service                                | Provider choice and model may improve multilingual/paraphrase recall                                                                                                                         | Network/provider outage, credential/retention/training policy, egress and latency, and another controller outside D1                                                              | **Only after gate**          |
| Workers AI embeddings plus Vectorize                           | Potentially co-located query/build path                                                                                                                                                      | Model availability, dimensions, throughput, cost, request-path generation risk, and provider lock-in remain unverified                                                            | **Only after gate**          |
| Hybrid lexical + vector                                        | Can measure complementarity and retain exact-term behavior                                                                                                                                   | More ranking complexity and harder explanation; vector false links can increase without evidence review; requires ablation and calibrated abstention                              | **Research comparison only** |

Cloudflare's current documentation records a maximum of 1,536 dimensions, 10
KiB metadata per vector, and a maximum `topK` of 50 when returning all metadata
or values. Those limits do not justify a production choice: Mathen must enforce
its lower query bounds, and the provider's limits must be rechecked at
implementation time. A Vectorize index would contain IDs and bounded filter
metadata only; D1/card hydration would remain authoritative.

## Evidence-based readiness assessment

| Criterion        | Current observation                                                                              | Decision consequence                                                                         |
| ---------------- | ------------------------------------------------------------------------------------------------ | -------------------------------------------------------------------------------------------- |
| Corpus size      | 2,481 eligible atomic records at the current snapshot                                            | Large enough for a pilot; not a reason by itself to pay operational complexity               |
| Evidence closure | 1,531 evidence records; no missing references in the audited card/features/views/relations paths | A pilot can measure locality and hydration; preserve fail-closed omissions                   |
| Scope metadata   | MTH-0143 reports zero specified scope dimensions and zero evidence scope contexts                | Block scope-sensitive production rollout; require an abstention/unknown slice                |
| Claim types      | Features are mostly facts; views include inference/hypothesis/analogy                            | Stratify metrics by claim type; similarity cannot upgrade claims                             |
| Freshness        | 1,527/1,531 evidence records have `accessed`; cards are pinned to heterogeneous commits/releases | Every run needs an immutable corpus digest and freshness distribution; no silent stale index |
| Privacy          | Queries may contain sensitive research text; no provider retention/training policy is selected   | Do not send text outside the deployment until policy and data minimization pass              |
| Cost             | Lexical has no embedding calls or vector index; vector cost is unmeasured                        | Require build/query/storage budget and alert before any rebuild or rollout                   |
| Latency          | No vector query p50/p95 or hydration latency measurement exists                                  | Benchmark under bounded Worker-like conditions before production consideration               |
| Explainability   | Lexical overlap is inspectable; vector scores are uncalibrated                                   | Vector result must show score kind, metadata, source, evidence, and abstention               |
| Abstention       | Contract supports empty/unavailable and explicit research abstention; no populated rate exists   | Treat unknown scope, stale source, and low-confidence candidates as first-class outcomes     |
| Existing metrics | MTH-0118/MTH-0134 define bounded discovery metrics, but no run compares methods                  | Do not claim vector benefit until the gated experiment produces a valid manifest             |

## Gated experiment (research only)

Proceed only if a separate task accepts the following gates. The experiment must
be offline or disposable, use no production binding/secret/index, and write
research artifacts outside `data/systems/`. The lexical baseline is the primary
control; vector-only and optional hybrid runs use the exact same frozen snapshot,
queries, filters, evidence budget, and reviewer rubric.

### Entry gates

1. Freeze `data/systems/` at an immutable commit and record the sorted corpus
   digest, document IDs, source digests, evidence bundle digest, and counts.
2. Validate every candidate document's local evidence closure and source path;
   exclude drafts, analyses, prompts, private artifacts, and negative-knowledge
   holdouts from candidate generation.
3. Include query slices for terminology variants, each record kind, all four
   claim types where available, explicit scope filters, freshness/version
   changes, and deliberately misleading similarities. A missing scope field is
   `unknown`, not a match.
4. Use at least two independent reviewers for high-impact labels and retain
   disagreement. Labels record evidence locality, claim type, scope match, and
   `relevant` versus `false-link`; no label asserts truth or compatibility.
5. Declare the embedding provider/model, dimensions, metric, normalization,
   representation/template version, retention/training policy, and cost model
   before the vector run. A provider-neutral fake index may be used for the
   first representation test, but it cannot support a deployment claim.

### Acceptance gates

The vector or hybrid method may advance to a disposable adapter review only if
the manifest validates and, against lexical at the same cutoffs:

- macro nDCG@10 improves by at least 0.05 **or** recall@10 improves by at least
  0.10 on the paraphrase/terminology-variant slice, with the slice denominator
  reported;
- evidence locality, scope completeness, and claim-type accuracy do not fall
  below the lexical control by more than 0.02 each;
- false-link rate does not increase by more than 0.02 overall or by more than
  0.05 in any claim-type stratum, and every held-out negative-knowledge query
  remains excluded from candidate generation;
- abstention is explicit and no worse than lexical on unknown/scope-mismatch
  queries; an apparent recall gain from returning unsupported records fails;
- p50/p95 query plus D1 hydration latency and provider error rate fit a written
  budget, with no query text or credentials in logs; and
- the privacy/retention review, cost estimate, rollback procedure, and
  explainability review are approved independently of the retrieval score.

No aggregate score can override a failed evidence, scope, privacy, false-link,
or abstention gate. A run with insufficient labels or empty denominators is
exploratory and cannot pass.

### Required output

Use `schemas/retrieval-evaluation-manifest.schema.json` and the existing
`validate-retrieval-evaluation` command. Run lexical, vector, and (if tested)
hybrid methods as separate manifests or a clearly declared comparison bundle.
Record recall@k, nDCG@k, evidence locality, claim-type accuracy, scope
completeness, false-link rate, abstention rate, p50/p95 latency, provider
errors, index/build size, and embedding calls/tokens in a companion research
record. The schema's bounded discovery metrics remain the acceptance source of
truth; latency/cost are operational observations, not truth metrics.

## Index versioning and rollback, if a gate passes

The first vector publication must be a new, replaceable index version, never an
in-place mutation of the active baseline. Use an ID containing corpus digest,
representation/template version, model ID, dimensions, metric, and normalized
scope/filter metadata schema. Build and verify offline, then publish a new
versioned index and atomically switch an active pointer only after:

1. document count and IDs equal the frozen manifest;
2. source and evidence digests hydrate from D1 without stale references;
3. no draft/private path or unapproved metadata is present;
4. filters, claim metadata, scope metadata, and deterministic tie behavior pass;
5. read smoke tests and the gated evaluation pass; and
6. budget, privacy, and rollback approvals are recorded.

Retain the prior verified version during a defined retention window. Rollback is
an atomic pointer change to the previous verified version; it never rewrites
cards, D1 rows, relations, or canonical evidence. A source digest mismatch,
missing evidence, provider outage, failed smoke test, budget breach, or privacy
incident makes the new version unavailable and restores the prior pointer (or
the explicit lexical action); it must never silently return stale or draft
prose. Every model, dimension, metric, template, corpus, scope metadata, or
filter-schema change creates a new index version.

## Unresolved questions

- Which offline or managed model meets the corpus language mix, privacy and
  retention requirements, and cost/latency budget?
- Can reviewers label enough paraphrase and misleading-similarity queries to
  make the proposed thresholds meaningful, especially with currently sparse
  scope metadata?
- What freshness policy should apply to evidence with missing `accessed` dates
  and to cards pinned to historical commits?
- Is a provider-neutral local experiment sufficient to decide representation
  value, or is a disposable Vectorize test required to measure managed latency?
- Who owns index publication, active-pointer auditing, and rollback during a
  failed rebuild?
