# Public research narrative proposal

**Issue:** MTH-0119 / [#49](https://github.com/Xuepoo/mathen/issues/49)
**Status:** planning and design artifact; not a claim that the proposed research
loop is complete or empirically validated.

## Purpose and audience

The public narrative should explain what Mathen is studying and how its current
artifacts support that study without presenting a research direction as a
finished architecture synthesizer. It should be readable from the README and
use the more detailed research documents as supporting references.

The primary audience is an engineer or researcher asking:

- What does Mathen actually observe and store?
- Where do humans, LLMs, retrieval, deterministic contracts, and experiments
  contribute different kinds of evidence?
- What does a cross-domain comparison mean, and what does it *not* mean?
- When is a result a discovery candidate, a reviewed observation, a useful
  prototype, or merely an analogy?

The narrative should use the existing claim vocabulary (`fact`, `inference`,
`hypothesis`, and `analogy`) and should preserve the distinction between the
current implementation, an open research hypothesis, and a future experiment.

## Proposed central thesis

Mathen is an evidence-backed intermediate representation for studying reusable
software architecture. It does not reduce a system to one essence, ask an LLM
to invent a final architecture, or treat a similarity result as proof. Its
research question is whether explicit, evidence-bounded representations can
help people move from observations about existing systems to testable candidate
architectures across communities.

The public wording should prefer:

> Mathen investigates whether a reviewed bridge between evidence, architectural
> microstructure, and checkable contracts can make cross-domain comparison and
> architecture synthesis more useful and more falsifiable.

It should avoid wording such as “Mathen discovers novel architectures” or
“Mathen proves that unrelated systems are equivalent.”

## The evidence-to-experiment loop

The narrative should show the following loop rather than a one-way
“LLM-in, architecture-out” pipeline:

```text
evidence
  → deterministic observation
  → reviewed architectural microstructure
  → mathematical or interface contract
  → bounded composition candidate
  → candidate macro-architecture
  → prototype, benchmark, or failure experiment
  → new evidence, counterexample, or negative knowledge
  ↺ human review and question reformulation
```

Each arrow has a different epistemic status:

1. **Evidence.** Start with source code, fixed revisions, design documents,
   papers, benchmarks, protocol specifications, or reproducible operational
   observations. Preserve provenance, version, and where applicable deployment
   origin.
2. **Deterministic observation.** Repository tooling can record reproducible
   observations such as tracked paths, language counts, build markers, and
   navigation signals. These observations prioritize review; they do not by
   themselves assert semantic architecture facts.
3. **Microstructure.** A microstructure is a bounded, reusable architectural
   unit described at an explicit scale: primitive, mechanism, subsystem,
   system, or ecosystem. It can name states, events, operations, boundaries,
   resources, failures, and validity scope. A microstructure is an
   evidence-linked candidate document, not an automatic promotion of a card.
4. **Contract.** A mathematical-view contract or typed-composition contract
   makes carriers, states, operations, relations, transitions, laws or checks,
   interfaces, preconditions, postconditions, resources, and failure modes
   explicit where the supplied data permits. A `valid` finite check means that
   the supplied model data passed that check; it does not prove that the whole
   implementation has the modeled semantics. Missing data remains
   `undetermined`.
5. **Composition.** A composition candidate records inputs, roles, constraints,
   preserved or weakened properties, conflicts, assumptions, validation gaps,
   and discovery provenance. Typed composition is deliberately bounded and
   remains `proven: false`; names, vector similarity, graph position, or LLM
   prose cannot silently create an adapter or a compatibility claim.
6. **Macro-architecture.** A candidate macro-architecture is an interpreted
   design hypothesis assembled from smaller structures under a target workload,
   deployment boundary, and constraints. It is not a canonical fact merely
   because its components are individually documented.
7. **Experiment.** A prototype, benchmark, property test, fault injection, or
   failure test evaluates a bounded question. Experiment evidence should retain
   the protocol, system commit, environment, command, dataset, repetitions,
   metrics, and artifacts. A result generalizes only within its stated scope.
8. **New evidence and review.** Results can strengthen, weaken, reject, or
   narrow a candidate. Counterexamples and bounded negative knowledge are useful
   outputs, not failures to hide. Human review decides what becomes canonical.

The loop is therefore an epistemic workflow, not an automatic synthesis
guarantee. The intended improvement is traceability: a reader should be able to
follow a candidate back to evidence and forward to the experiment that could
change the claim.

## Division of labor

The public narrative should present the following roles as complementary and
non-interchangeable:

| Participant or mechanism | Role in the loop | Boundary |
| --- | --- | --- |
| Human researcher | Reframes the question, selects a surprising or useful path, identifies scope, judges trade-offs, reviews claims, and decides what to test | Human judgment is not automatically reproducible, and review remains a bottleneck |
| Deterministic repository tooling | Resolves fixed revisions and records reproducible source/tree observations | Path and build signals are navigation evidence, not semantic architecture claims |
| LLM | Explains local evidence, proposes abstractions, compares distant structures, and drafts candidate mappings or cards | Output follows the prompt and available evidence; it is not proof, a theorem, an implementation guarantee, or an autonomous architecture authority |
| Graph retrieval or analysis | Exposes typed neighborhoods, communities, paths, bridges, centrality, and possible cross-community routes | A graph projection describes the selected data and relations; position is not importance, truth, causality, or compatibility |
| Vector retrieval | Recovers terminology variants and semantically distant candidate records | Similarity is a recall signal, not a typed relation, causal link, or composition result |
| Microstructure and mathematical contracts | Make scale, scope, assumptions, interfaces, operations, and checkable properties explicit | A contract checks supplied finite/model data and cannot validate omitted implementation behavior |
| Experiment and failure test | Measures runtime behavior, trade-offs, counterexamples, and reproducibility | Results are workload-, version-, environment-, and deployment-scoped |

The required separation is:

```text
vector similarity ≠ graph position ≠ LLM interpretation
                ≠ contract classification ≠ runtime compatibility
                ≠ historical influence
```

Retrieval can suggest a question. It cannot answer the question merely by
returning a neighbor.

## Cross-domain analogies: useful language with explicit limits

Cross-domain analogies are a way to state a bounded structural resemblance. They
are not canonical relations, implementation dependencies, formal equivalences,
substitutability claims, or evidence of historical influence. Each published
analogy should identify the source and target concepts and scale, shared and
preserved properties, non-preserved properties, conditions, exclusions, at
least one counterexample, local evidence, and an explicit non-equivalence
statement.

### Chemistry and biology

The existing reaction-network/gene-regulation example compares directed
network motifs and changing state variables. It preserves only a qualitative,
motif-level graph resemblance. Chemical kinetics and transcriptional
regulation do not share parameters, substrates, governing laws, measurement
units, or necessarily the same causal and temporal semantics. A matching motif
does not justify parameter transfer, a shared simulation, causal equivalence,
or historical influence.

This is the model wording to reuse publicly: **a representation can transfer a
question about connectivity without transferring the mechanism that produces
the behavior.**

### Materials science

Materials science is a proposed explanatory analogy for the term
“microstructure,” not evidence that software has a physical material substrate.
At a bounded level, material phases, defects, processing conditions, interfaces,
and resulting properties can illustrate why a system should be described by
small structures, boundary conditions, and observed properties rather than by a
single product label. A software microstructure can similarly expose a bounded
mechanism, interface, lifecycle, resource effect, or failure mode.

The analogy must not import crystal structure, thermodynamic laws, constitutive
equations, scale invariance, or material-property predictions into software.
Software microstructures are contextual, versioned, observational, and
deployment-scoped. The analogy is useful for asking which properties are
preserved across a transformation; it is not a materials model or a claim that
software composition obeys physical laws.

### Taxonomy and classification

Taxonomy is a proposed analogy for organizing reusable architectural vocabulary.
The current feature taxonomy is a controlled, backward-compatible descriptive
vocabulary (`kind`, `domain`, `layer`, and open `pattern_id`), not a discovery
of natural kinds. Categories help retrieval, comparison, and review; they do
not assert that systems belong to mutually exclusive or complete ontological
classes. A feature may have several valid views, and a new pattern may be
proposed before it is registered.

Taxonomic similarity must therefore remain weaker than a typed relation. It does
not establish dependency, implementation lineage, composition compatibility, or
historical influence. Taxonomy can make a candidate visible; evidence and
contracts must still justify what the candidate means.

## What “discovery” and “novelty” mean here

The public narrative should use **discovery** cautiously. In the first instance,
discovery means that a search or researcher surfaced a candidate path, mapping,
counterexample, or question that was not previously recorded in the current
dataset. It does not mean that Mathen created a new fact, found a historically
unknown influence, or generated a useful architecture.

Likewise, **novelty** must be decomposed rather than assigned from fluent prose
or graph density. A candidate may be new in:

- topology or the relationship between components;
- composition boundary or interface;
- constraints, target workload, or deployment context;
- preserved, weakened, or newly introduced behavior;
- a tested trade-off or operational arrangement; or
- only its wording or representation.

Only the last category is textual novelty. A cross-community path, an LLM
proposal, a larger graph, or a vector-nearest neighbor is not evidence of
architectural originality. A stronger novelty claim requires a defined prior
reference set, an explicit scope, source review, and—where the claim concerns
usefulness or behavior—a prototype or experiment. The open benchmark questions
in `docs/research-instrument.md` should remain visible rather than being
replaced by an uncalibrated confidence score.

## Current capabilities and limitations

The public narrative should claim only the following current capabilities:

- versioned Architecture Cards with evidence-linked claims and semantic
  validation;
- fixed-commit repository analysis and reproducible modeling bundles;
- deterministic repository observations that guide semantic review;
- an evidence-bounded, provider-neutral OpenAI-compatible LLM adapter that
  writes drafts and protocol sidecars rather than canonical cards;
- scale-aware microstructure documents with explicit state, operation,
  boundary, resource, failure, and validity fields;
- checkable mathematical-view contracts with finite classifications of
  `valid`, `invalid`, or `undetermined` for supported model families;
- typed, bounded composition candidates that retain discovery provenance and
  `proven: false`;
- standalone cross-domain analogy mappings with non-equivalence and
  counterexample requirements;
- standalone negative-knowledge records for bounded invalid or misleading
  candidates;
- D1 as the canonical structured store, with optional rebuildable semantic
  retrieval and read-only API/MCP surfaces; and
- a browser/API/MCP deployment boundary that keeps reviewed cards separate from
  drafts and modeling evidence.

The narrative must also state what is *not* currently provided:

- no automatic proof that an implementation satisfies a mathematical model;
- no theorem-producing or invertible microstructure representation;
- no automatic promotion of LLM output, analogy mappings, or compositions to
  reviewed knowledge;
- no guarantee that graph/vector retrieval finds all relevant systems or that
  retrieval candidates are compatible;
- no general-purpose graph database requirement or claim that the current
  relational projection captures every useful traversal;
- no calibrated probability, originality score, or universal architecture
  quality score;
- no automatic historical-influence inference from structural similarity;
- no substitute for source review, benchmarks, failure tests, or domain
  expertise; and
- no validated claim that the full evidence-to-experiment loop improves
  discovery, review time, or architecture quality. Those are experiments to
  design and measure.

## Deployment and provenance origins

The narrative should never make a deployment hostname part of the research
identity. A microstructure, mathematical contract, analogy, composition, or
experiment should state the versions, conditions, exclusions, and applicable
`deployment_origins` in its validity scope. Values such as
`local-analysis`, `configured-research-origin`, a preview origin, or a named
production origin describe where a claim was evaluated; they do not turn an
origin into evidence.

This principle applies to the implementation as well:

- D1 remains the structured source of truth while semantic indexes are
  rebuildable;
- browser requests use the deployment's same-origin `/api` boundary;
- MCP and synchronization origins are configurable through documented settings;
- OpenAI-compatible LLM endpoints are selected by explicit configuration or
  environment variables; and
- secrets remain outside URLs and checked-in research records.

The public examples should use placeholders or configuration names, not imply
that `mathen.example.com`, a particular provider, or a local endpoint is
required. A deployment origin scopes a reproduction and access path; it does
not establish semantic validity or historical identity.

## Proposed public-facing structure

When this proposal is implemented in README/web copy, keep the top-level story
short and link to the detailed documents:

1. **What Mathen studies:** evidence-backed, temporal architectural
   intermediate representations and bounded synthesis questions.
2. **The loop:** evidence → observation → microstructure → contract →
   composition → macro candidate → experiment → new evidence.
3. **Who does what:** human, deterministic tooling, LLM, graph/vector
   retrieval, contracts, and experiments.
4. **How to read comparisons:** facts, inferences, hypotheses, and analogies;
   chemistry/biology, materials, and taxonomy examples with explicit
   non-equivalence.
5. **What discovery means:** candidate surfacing is not proof, originality, or
   compatibility.
6. **Current status:** implemented contracts and interfaces versus open
   research questions and limitations.
7. **Reproduction boundary:** fixed evidence, validity scope, configurable
   deployment origins, and review status.

Suggested links are `docs/research-instrument.md`,
`docs/microstructure-ontology.md`, `docs/mathematical-view-contracts.md`,
`docs/temporal-composition-contract.md`, `docs/cross-domain-analogies.md`,
`docs/negative-knowledge-contract.md`, `docs/llm-modeling.md`, and
`docs/configuration.md`.

## Scope and acceptance criteria for a future implementation

This issue should result in a documentation-only narrative update. It should
not add a graph database, change card schemas, promote drafts, add a new
retrieval provider, or claim that a future experiment has already succeeded.

A later implementation is ready for review when:

- the README or web-facing entry point contains the loop and role boundaries;
- every capability statement can be traced to an existing command, schema,
  contract, or documented boundary;
- chemistry/biology, materials, and taxonomy comparisons are labeled as
  analogies or hypotheses with explicit exclusions;
- discovery and novelty language is scoped and does not imply proof;
- current limitations and open evaluation questions remain visible;
- examples keep deployment origins configurable and do not hardcode a research
  identity; and
- documentation checks pass without modifying canonical cards or generated
  build output.

The next research issue can add a reviewed benchmark, experiment protocol, or
negative result. Until then, this proposal should be read as the intended
public position, not as evidence that the complete loop has been validated.
