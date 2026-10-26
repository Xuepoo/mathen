<!-- markdownlint-disable MD060 -->

<!-- markdownlint-disable MD013 -->

# Mathen as a research instrument

Mathen is intended to study how software architecture can be explored across
domains, not to ask an LLM to generate a final architecture from a familiar
template. This document records the current research position and the
questions that still require evidence. It is a research hypothesis and design
direction, not a claim that the full loop has already been validated.

## Position and method in one view

Mathen is an evidence-bounded **Architecture Exploration Methodology**: a
research instrument for moving from evidence about existing systems to
reviewable, testable candidate structures. Its purpose is exploration and
traceability, not autonomous architecture generation. The operative loop is:

```text
evidence
  → deterministic observation
  → architectural microstructure
  → contract
  → bounded composition
  → prototype or experiment
  → new evidence, counterexample, or negative knowledge
```

The arrows are not interchangeable transformations. Evidence is selected and
scoped; observations are reproducible signals; microstructures are bounded
interpretations; contracts make assumptions and checks explicit; compositions
state conflicts and validation gaps; experiments measure behavior under a
declared workload and environment. Human review can stop, narrow, reject, or
redirect the loop at every stage.

**Discovery** asks what a person or tool should inspect next: a lexical result,
graph path, LLM suggestion, analogy, counterexample, or review question.
**Synthesis** asks whether reviewed structures can be assembled under explicit
constraints into a candidate worth prototyping. A discovery signal is not a
synthesis result, and a synthesis candidate is not an implemented or superior
architecture.

## The human–LLM complement

Human researchers and language models contribute different capabilities:

| Participant            | Primary contribution                                                                            | Boundary                                                                                               |
| ---------------------- | ----------------------------------------------------------------------------------------------- | ------------------------------------------------------------------------------------------------------ |
| Human researcher       | Problem reframing, curiosity, unusual questions, research direction, and final review           | Human insight is difficult to scale and is not automatically reproducible                              |
| LLM                    | Broad cross-domain retrieval, local explanation, candidate abstractions, and candidate mappings | Output follows prompts and available evidence; it is not proof, a theorem, or an engineering guarantee |
| Graph analysis         | Communities, centrality, paths, bridges, and structural positions                               | A graph metric describes the current projection, not intrinsic importance or truth                     |
| Retrieval (current lexical; planned vector) | Lexical retrieval provides explainable discovery; a future vector index could provide terminology alignment and distant candidates | Retrieval scores are candidate signals, not typed relations, compatibility, or proof; vector integration is not implemented |
| Mathematical contracts | Deterministic checks, assumptions, laws, scope, and property classifications | A finite check validates supplied finite/model data, not the entire implementation |
| Experiments            | Runtime behavior, counterexamples, failure modes, and new evidence                              | An experiment has a workload and scope; it does not automatically generalize                           |

The intended division of labor is:

```text
human question and reframing
              ↓
graph candidate discovery and planned vector candidate discovery
              ↓
LLM explanation and structural hypothesis
              ↓
evidence-bounded microstructure mapping
              ↓
mathematical contract and deterministic checks
              ↓
prototype, experiment, or failure test
              ↓
human review and new evidence
```

LLM output remains under `data/drafts/` or in a research candidate record. It
does not become canonical knowledge without deliberate human review. The
evidence-bounded protocol is described in
[`llm-modeling.md`](llm-modeling.md). This document does not rely on an
external decision-record identifier for provenance.

### Replaceable extraction provenance

An extraction or graph run must identify the stage that produced each
candidate. The current replaceable model profile is recorded as:

```text
provider/model: openai/gpt-6-astra
thinking level: high
role: feature extraction and graph construction/annotation
```

This is extraction provenance, not an architecture authority or a claim about
the model's superiority. Another provider or model may perform the same role
when the evidence boundary, prompt/schema versions, deterministic inspection,
and review protocol are held constant. A profile change creates a distinct
run; it must not overwrite the earlier interpretation. Secret-safe sidecars
should retain the model profile, input/evidence digest, source revision,
inspection provenance, output digest, review status, and canonical status, but
not API keys or other secret configuration. See
[`llm-modeling.md`](llm-modeling.md) for the implemented protocol and
provenance boundary.

## Why direct LLM architecture design is insufficient

An unconstrained request such as “design a new database” or “design a new
agent runtime” can produce a coherent answer while still following common
patterns from the model's training and prompt context. Coherence is not
architectural novelty. A fluent answer can also hide missing assumptions,
unexamined trade-offs, and unsupported claims.

This is not a claim that Transformers cannot make distant associations. They
can perform many kinds of analogy and multi-step reasoning. The research
question is narrower: given a large knowledge space, what causes a model to
explore a low-salience or cross-community path rather than produce the most
available template? Possible factors include representation, search strategy,
prompt objectives, evaluation feedback, tool use, and the limits of the
available evidence. The relative contribution of the Transformer architecture
itself remains an open question and must not be assumed from an isolated
failure.

Humans are not uniformly better at this task either. Human advantage may come
from problem reformulation, curiosity, goals, embodied experience, and
willingness to pursue an apparently unrelated observation. Mathen should make
those exploratory decisions explicit rather than pretending that a model's
first answer is discovery.

## Separate discovery signals from validated relations

Mathen must keep the following signals separate:

```text
vector similarity
  ≠ graph similarity
  ≠ LLM interpretation
  ≠ mathematical validity
  ≠ runtime compatibility
  ≠ historical influence
```

A candidate record should preserve, where available:

- discovery method: `graph`, `vector`, `llm`, `human`, or `combined`;
- source and target communities;
- the cross-community path or representation change that produced the candidate;
- source evidence, prompt/model provenance, and deterministic observations;
- shared, preserved, weakened, conflicting, and unverified properties;
- counterexamples, disagreement, negative results, and review status;
- the scope and assumptions under which the candidate was proposed.

Candidate composition remains `proven: false` until the relevant contracts,
experiments, and review support a stronger claim. Similarity search must never
silently create `uses`, `composes`, `refines`, `influenced-by`, or canonical
feature relations.

The same rule applies to every shortcut in the loop:

```text
similarity ≠ graph path ≠ typed relation ≠ proof
          ≠ compatibility ≠ causality ≠ originality
          ≠ architecture quality or superiority
```

A graph path is a path through the selected projection, not a causal history.
A relation is valid only when its type and local evidence support that relation.
A contract result classifies supplied model data; it does not prove omitted
implementation behavior. An experiment supports only its declared system
revision, workload, runtime conditions, scale, and failure boundary. No result
may silently generalize from one deployment, lifecycle state, or scope to
another.

## Representation bridges: the Cartesian analogy

The development of analytic geometry is a useful historical analogy for the
kind of representation problem Mathen is studying. In the seventeenth century,
Descartes and Fermat helped establish systematic methods for expressing
geometric objects and conditions with coordinates and algebraic equations. A
circle, for example, can be represented by:

```text
(x - a)^2 + (y - b)^2 = r^2
```

The important change was not the introduction of a shorter notation. It was the
creation of a working bridge between two previously distinct practices:

```text
geometric object and condition
        ↕ representation / interpretation
coordinate and algebraic expression
```

Once the bridge was available, algebraic operations could help answer geometric
questions, and geometric interpretation could constrain the meaning of
algebraic results. The bridge did not make every algebraic expression a valid
geometric object; its meaning depended on the representation, domain, and
conditions of interpretation. Analytic geometry also developed through the work
of more than one mathematician, so this is not a claim that one person alone
created all of the later theory.

The corresponding Mathen research hypothesis is:

```text
real software system and evidence
        ↕ abstraction / realization
architecture microstructure and mathematical contract
        ↕ typed composition / validation
candidate macro architecture
```

The hoped-for bridge would allow a documented system to be represented as
states, operations, boundaries, invariants, resources, failures, and typed
relations. A contract could then support bounded comparison or derivation, and
the result could be interpreted back as a candidate architecture and tested in
an implementation. This would be stronger than putting different systems in a
shared graph merely because their names or descriptions are similar.

The analogy is deliberately limited. Mathen does not currently have the mature
mathematical objects, invertible representation rules, or theorem-producing
semantics of analytic geometry. A software microstructure may be partial,
context-dependent, historically changing, or only observationally identified.
The following are therefore open research questions:

- What information must a system-to-microstructure mapping preserve?
- When is a mapping a refinement, a realization, a projection, or only an
  analogy?
- Which operations on a microstructure have a meaningful interpretation in the
  source system and in a candidate target system?
- Which properties survive translation, and which are weakened or lost?
- Can a candidate generated in the shared representation predict a useful
  implementation or experiment?
- What counterexamples show that the representation bridge is too coarse?

The intended standard is not “make everything translatable”. It is to find
small, evidence-bounded bridges whose assumptions, preserved properties,
non-preserved properties, and failure conditions are explicit. In Mathen's
claim vocabulary, the Cartesian comparison is an `analogy` and the proposed
software representation bridge is a `hypothesis` until those conditions are
validated.

## Cross-community discovery

Nearest-neighbor retrieval is useful for recall, but it is not enough for the
research goal. Mathen should eventually search through several routes:

1. same-community semantic neighbors;
2. graph bridges and high-betweenness paths;
3. distant communities connected through a shared microstructure;
4. alternative representations of the same question;
5. deliberately selected counterexamples and negative knowledge.

For example, a future candidate search might ask whether database recovery
boundaries and agent execution histories share a bounded replay structure. That
is a research hypothesis, not an equivalence between databases and agents. The
candidate must state what is shared, what is not transferred, and how it could
be tested.

## Questions for future evidence

The following questions should remain visible until evaluated:

### Search and representation

- Does explicit microstructure representation improve cross-domain bridge
  recall over product-name or feature-text retrieval?
- Do graph paths discover useful candidates that vector nearest neighbors miss?
- Do vector methods recover terminology differences without increasing false
  links?
- Does asking an LLM to compare distant structures produce better candidates
  than asking it to design a complete system directly?
- Which representations encourage useful problem reframing rather than familiar
  template completion?

### Validation and review

- What fraction of LLM-proposed bridges survive source review?
- How often do mathematical contracts reject an attractive analogy?
- Which counterexamples most effectively prevent repeated false links?
- Does the structured workflow reduce expert review time without hiding
  uncertainty?
- Can experiments distinguish a useful architectural transfer from an elegant
  but non-predictive analogy?

### Novelty and usefulness

- Is a candidate novel in topology, composition, constraints, behavior, or
  deployment, rather than merely novel in wording?
- Does a cross-community candidate lead to a useful prototype or experiment?
- Does the system discover anything that a strong domain expert would not find
  with ordinary search, and at what review cost?
- Which graph/vector/LLM combinations improve validated candidate value rather
  than just graph density?

The planned evaluation should also separate these questions operationally:

- Does a human using the loop find more useful cross-community candidates, or
  merely more candidates, than a direct search or direct LLM-design control?
- Does explicit microstructure improve bridge precision, evidence locality,
  scope preservation, and reviewer usefulness at a tolerable review cost?
- Do contracts reject attractive but invalid or under-specified candidates, and
  do they abstain when observations are missing rather than manufacture a
  negative result?
- Do prototypes or failure tests distinguish a useful transfer from a fluent,
  non-predictive analogy? What counterexamples are discovered and retained?
- Are findings stable across source revisions, model/provenance profiles,
  graph projections, deployment origins, and lifecycle/scope partitions?

## Evaluation dimensions

Mathen should evaluate this research instrument with separate metrics instead
of a single confidence score:

```text
cross-community candidate recall
bridge precision and false-link rate
evidence and citation locality
mathematical-contract rejection rate
counterexample discovery rate
reviewer usefulness and review-time change
validated candidate usefulness
community stability across graph updates
graph/vector disagreement and complementarity
```

The metrics require reviewed reference sets, explicit scopes, and documented
limitations. A denser graph is not automatically a better graph. A more novel
textual answer is not automatically a novel architecture.

## Implemented evidence and future hypotheses

The current repository supports evidence-linked cards and drafts, fixed-commit
repository observations, modeling bundles, semantic validation, microstructure
and mathematical-view contracts, bounded composition candidates, read-only
graph/API/MCP projections, and a bounded lexical retrieval baseline. It does
not implement autonomous synthesis, a semantic/vector index, theorem
production, calibrated originality or quality scoring, or a general graph
database.

The retrieval boundary is intentionally empirical. The offline MTH-0150 pilot
found equal Recall@5 for lexical and local vector candidates (10/12) and lower
vector nDCG@5 (0.5464 versus 0.5579), with approximately 280.8 seconds of CPU
document-embedding time. The larger MTH-0154 evaluation retains the lexical
control and records unknown scope coverage rather than inventing a vector
comparison. Therefore lexical retrieval remains the explainable baseline;
embeddings and Vectorize remain a future research comparison gated by reviewed
labels, scope/claim-type slices, false-link and abstention checks, latency, and
cost. See [`mth-0150-retrieval-embedding-pilot.md`](mth-0150-retrieval-embedding-pilot.md),
[`mth-0154-retrieval-evaluation.md`](mth-0154-retrieval-evaluation.md), and
[`retrieval-extension-decision-mth-0147.md`](retrieval-extension-decision-mth-0147.md).

Scope and lifecycle pilots reinforce the same boundary. The
[`scope-context-contract.md`](scope-context-contract.md) keeps validity scope,
workload, runtime conditions, scale, and failure conditions independent; the
[`lifecycle-status-contract.md`](lifecycle-status-contract.md) keeps feature
lifecycle separate from claim type and review status. Missing fields mean
unknown or not recorded, not absence, currentness, compatibility, or failure.

Small SQLite observations show how the experiment stage should be read. The
transaction rollback observation and its follow-up savepoint observation are
fixed, local, sequential protocols with explicit exclusions; they do not
constitute a general recovery theorem or universal SQLite behavior. See
[`g5-sqlite-transaction-experiment.md`](g5-sqlite-transaction-experiment.md).
The related savepoint note, when present in the research artifact set, is
similarly a detached observation rather than a canonical-card claim.

Related internal review material includes the extraction/review boundary in
[`review-extraction-pipeline.md`](review-extraction-pipeline.md), the
scope/lifecycle contracts above, and the synthesis evaluation plan in
[`mth-0118-synthesis-validation-benchmark.md`](mth-0118-synthesis-validation-benchmark.md).
Supporting records include the [internal literature map](../paper/README.md),
[replaceable extraction provenance profile](extraction-provenance.md),
[review-queue audit](mth-0159-research-review-queue.md),
and [SQLite savepoint observation](mth-0164-sqlite-savepoint-observation.md).
These are commit-pinned research records, not a paper body, canonical card, or
production claim.

## Current status and related work

The repository already contains the first pieces of this direction:

- evidence-bounded LLM protocol and secret-safe provenance sidecars;
- scale-aware architecture microstructure contracts;
- checkable mathematical-view contracts;
- explicit cross-domain analogy mappings with non-equivalence and
  counterexamples;
- bounded composition candidates that remain `proven: false`;
- read-only graph/API/MCP boundaries.

The presence of a schema, validator, fixture, or research harness is not the
same as a populated corpus or a public data surface. D1/API/MCP expose only
data loaded into their configured stores and read boundaries; local filesystem
mode can inspect repository artifacts explicitly. The MTH-0118 plan is linked
to its present research-only harness in
[`mth-0118-benchmark-harness.md`](mth-0118-benchmark-harness.md); that harness
validates supplied manifests and metrics but does not execute experiments or
publish results.

The following research issues extend the instrument:

- [#40](https://github.com/Xuepoo/mathen/issues/40): architecture microstructure
  and composition science;
- [#44](https://github.com/Xuepoo/mathen/issues/44): typed composition semantics;
- [#47](https://github.com/Xuepoo/mathen/issues/47): graph projections;
- [#48](https://github.com/Xuepoo/mathen/issues/48): synthesis validation and
  novelty benchmarks.

The next implementations should add evidence, schemas, experiments, and
negative results to this document rather than replacing these open questions
with unsupported conclusions.
