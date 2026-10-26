<!-- markdownlint-disable MD013 -->

# Mathen internal literature map

- **Status:** internal research note, not a paper or submission artifact
- **Search date:** 2026-10-27
- **Source set:** bounded arXiv reconnaissance supplied by the commander
- **Method:** targeted metadata and abstract inspection of the supplied arXiv IDs;
this is **not a systematic literature review**.

This map records prior art and useful neighboring ideas for Mathen. It is not a
claim that the listed work is exhaustive, that every abstract claim has been
independently reproduced, or that Mathen is novel relative to any individual
paper. The classifications below are working research labels:

- **Precedent:** a directly relevant earlier idea, representation, workflow, or
  evaluation practice that Mathen must acknowledge and learn from.
- **Neighbor:** a related problem or method with useful overlap, but a different
  object, boundary, evidence regime, or evaluation target.
- **Contrast:** a useful boundary case whose differences help state what Mathen
  does and does not attempt.

## Source and reproducibility notes

- The authoritative landing pages are the versioned arXiv links in each entry.
  Version numbers are recorded as observed on the search date; later versions
  may change the interpretation.
- The source set is intentionally bounded to the 14 IDs below. No adjacent
  papers are added in this first map.
- Semantic Scholar citation-graph requests were rate-limited for some papers.
  A missing graph result must **not** be interpreted as an empty citation graph,
  absence of prior art, or evidence of novelty.
- Titles, dates, categories, and high-level relevance were checked against the
  arXiv API metadata and abstracts. Claims about methods, datasets, and results
  should be verified against the paper before being used as evidence in a
  future research artifact.
- This note does not establish historical influence. A shared structure is an
  analogy or neighboring design until a source supports influence.

## What Mathen is investigating

The likely Mathen gap is not “architecture knowledge management” in general.
The narrower engineering question is whether an evidence-bounded knowledge
base can make **cross-system microstructures**—small reusable architectural
features, relations, mathematical views, constraints, and trade-offs—searchable
and comparable while preserving:

1. **Claims, scope, and provenance:** every claim is typed, bounded to a system
   and version/context, and linked to local evidence rather than detached prose.
2. **Contracts:** schema and relation contracts make inputs, assumptions,
   preserved properties, conflicts, and uncertainty explicit.
3. **Negative knowledge:** unsupported relations, failed extraction, missing
   evidence, and rejected interpretations remain visible instead of becoming
   silent omissions or false facts.
4. **Reproducible observation:** repository observations are tied to fixed
   commits, commands, evidence IDs, and repeatable analysis artifacts.
5. **Discovery versus synthesis:** retrieval and comparison are separated from
   the later synthesis of candidate views or compositions; a generated
   hypothesis is not promoted to a reviewed fact.
6. **An experiment loop:** proposed views and compositions can be checked with
   explicit assumptions and operational experiments without being presented as
   automatic proofs.

These are a working gap statement, not a novelty claim. The papers below show
that each ingredient has substantial prior art in isolation or in adjacent
settings.

## Map at a glance

| Theme | IDs | Main relationship to Mathen |
| --- | --- | --- |
| Architecture knowledge management | 2005.08393, 2309.11572, 2103.11705 | Precedent for capturing, finding, and communicating AK; Mathen narrows the evidence and cross-system contract. |
| Architecture recovery | 2311.04643 | Neighbor and partial precedent for multi-source recovery and evaluation. |
| Design-space exploration and formal modeling | 1909.06809, 1603.00636 | Neighbors for explicit models, alternatives, invariants, and formal reasoning. |
| MBSE and interoperability | 2302.03503, 2601.07301 | Neighbors for model boundaries, decision capture, and tool contracts. |
| LLMs and software architecture | 2505.16697 | Survey precedent for task and evaluation coverage; not a Mathen implementation. |
| Knowledge-driven multi-agent design | 2503.20536, 2507.21382, 2602.04445, 2601.19548 | Neighbors and recent prior art for agentic extraction, design, validation, and structured AKM. |
| Benchmarks and evaluation | 2606.29520 | Neighbor/contrast: LLM competency benchmark, not repository evidence or cross-system synthesis evaluation. |

## Detailed entries

### Architecture knowledge management

#### 2005.08393v1 — Capturing Software Architecture Knowledge for Pattern-Driven Design

- **Year:** 2020
- **Categories:** `cs.SE`
- **Classification:** **precedent**
- **Theme:** pattern knowledge, quality attributes, decision support
- **Why it matters to Mathen:** This is direct prior art for organizing
  architectural knowledge around patterns, quality attributes, systems where
  patterns occur, and pattern combinations. Its review-and-practitioner
  evaluation framing is a reminder that reusable architecture knowledge needs
  both structured relationships and user-facing usefulness.
- **Likely Mathen use:** Use as a precedent when defining feature/quality
  attribute links, pattern-like microstructures, candidate relations, and
  retrieval questions. Compare its decision-support unit with Mathen's
  evidence-linked card and relation units.
- **Explicit non-claims:** Mathen must not claim to invent architecture
  knowledge capture, pattern-to-quality-attribute mapping, pattern combination
  analysis, or practitioner validation. This map does not verify the paper's
  full pattern inventory or empirical results.
- **Source:** <https://arxiv.org/abs/2005.08393v1>

#### 2309.11572v1 — Architecture Knowledge Representation and Communication Industry Survey

- **Year:** 2023
- **Categories:** `cs.SE`
- **Classification:** **precedent**
- **Theme:** industry representation, communication, views, ADRs,
  sustainability
- **Why it matters to Mathen:** The survey foregrounds the practical problem
  of representing and communicating architectural knowledge across stakeholders
  and the need to connect architectural features and viewpoints. That supports
  Mathen's insistence that a useful card is more than an isolated description.
- **Likely Mathen use:** Use its practitioner-oriented framing to test whether
  evidence links, scope, claim types, and relation views are understandable to
  different consumers. Treat stakeholder-specific views as a usability
  requirement, not as permission to duplicate unsupported claims.
- **Explicit non-claims:** Mathen must not claim to be the first system to
  connect views, features, ADRs, or stakeholder communication. A single-bank
  survey cannot establish general industry prevalence, and this map does not
  generalize its findings.
- **Source:** <https://arxiv.org/abs/2309.11572v1>

#### 2103.11705v1 — Exploring Web Search Engines to Find Architectural Knowledge

- **Year:** 2021
- **Categories:** `cs.SE`
- **Classification:** **precedent**
- **Theme:** architectural knowledge discovery, retrieval, relevance
- **Why it matters to Mathen:** This empirical study treats finding relevant,
  current architectural knowledge as a first-class engineering problem. It
  provides a useful contrast between open-web retrieval and Mathen's bounded,
  evidence-addressable repository corpus.
- **Likely Mathen use:** Use it to define retrieval evaluations around source
  relevance, knowledge type, stakeholder task, freshness, and decision context.
  It also motivates recording why a result was retrieved and what evidence a
  user can inspect.
- **Explicit non-claims:** Mathen must not claim that a local corpus always
  outperforms web search, or that retrieval ranking alone solves architecture
  knowledge quality. The study population, search engine behavior, and task
  design do not establish universal retrieval results.
- **Source:** <https://arxiv.org/abs/2103.11705v1>

### Architecture recovery

#### 2311.04643v1 — Software Architecture Recovery with Information Fusion

- **Year:** 2023
- **Categories:** `cs.SE`
- **Classification:** **neighbor** (with a partial **precedent** for
  multi-source evidence fusion)
- **Theme:** architecture recovery, dependencies, code text, folder structure,
  evaluation against ground truth
- **Why it matters to Mathen:** SARIF demonstrates the value of fusing several
  repository signals rather than treating one structural source as sufficient.
  Its use of labeled projects and architecture-similarity metrics is relevant
  to reproducible observation and extraction-quality evaluation.
- **Likely Mathen use:** Borrow the discipline of recording input signals,
  fusion decisions, ground truth or review references, and evaluation metrics.
  Mathen can use recovery output as candidate evidence, then keep extraction,
  claim typing, review, and cross-system synthesis as separate stages.
- **Explicit non-claims:** Mathen must not claim a new architecture-recovery
  algorithm, the reported accuracy improvement, or that card extraction is
  equivalent to recovering a ground-truth architecture. Recovered structure is
  not automatically a reviewed semantic claim.
- **Source:** <https://arxiv.org/abs/2311.04643v1>

### Design-space exploration and formal modeling

#### 1909.06809v5 — Architecture Definition in Complex System Design Using Model Theory

- **Year:** 2019 (version 5 observed in 2020)
- **Categories:** `cs.SE`
- **Classification:** **neighbor**
- **Theme:** architecture definition, system models, model theory, MBSE
- **Why it matters to Mathen:** This paper supplies a formal vocabulary for
  relating systems, models, and architecture definitions, and demonstrates the
  engineering use of a mathematically based definition process. It is relevant
  to Mathen's mathematical-view contract and its requirement to state a
  question and assumptions.
- **Likely Mathen use:** Use as a boundary reference when a Mathen mathematical
  view needs to distinguish a model, its interpretation, and the architecture
  claim being made. Require explicit scope and assumptions before using a
  formal lens.
- **Explicit non-claims:** Mathen must not claim to provide a new foundation
  for architecture definition, to formalize every card, or to inherit the
  paper's model-theoretic guarantees. A candidate mathematical view is not an
  automatic formal proof of a system property.
- **Source:** <https://arxiv.org/abs/1909.06809v5>

#### 1603.00636v1 — Semi-Automated Design Space Exploration for Formal Modelling

- **Year:** 2016
- **Categories:** `cs.SE`, `cs.LO`
- **Classification:** **neighbor**
- **Theme:** design alternatives, patterns, automated theory formation,
  invariants, fault analysis
- **Why it matters to Mathen:** The paper connects modeling patterns,
  alternative exploration, automated reasoning, and designer guidance. This is
  a strong conceptual neighbor for Mathen's separation between discovering
  candidate structures and evaluating them under explicit assumptions.
- **Likely Mathen use:** Use as prior art for an experiment loop: retrieve
  candidate microstructures, state invariants or questions, explore alternatives
  and conflicts, and report what was or was not checked. Keep human review and
  evidence provenance visible around generated alternatives.
- **Explicit non-claims:** Mathen must not claim automated theory formation,
  formal invariant discovery, or fault-model analysis merely because it stores
  mathematical views. A Mathen composition record describes a hypothesis and
  constraints; it does not prove that composed systems work.
- **Source:** <https://arxiv.org/abs/1603.00636v1>

### Model-based systems engineering and interoperability

#### 2302.03503v2 — Tool interoperability for model-based systems engineering

- **Year:** 2023
- **Categories:** `cs.SE`
- **Classification:** **neighbor**
- **Theme:** tool interoperability, model translation, service-oriented MBSE
- **Why it matters to Mathen:** The paper makes translation between equivalent
  models and the contract between discipline-specific tools central to an MBSE
  workflow. That is useful precedent for treating schema, evidence, and relation
  boundaries as explicit interfaces rather than incidental serialization.
- **Likely Mathen use:** Use its interoperability framing to document import /
  export boundaries, normalization assumptions, and what information may be
  lost when an observation enters the knowledge base. A future experiment loop
  can treat analyzers and reviewers as tools with declared contracts.
- **Explicit non-claims:** Mathen must not claim to implement MBSE tool
  interoperability, semantic equivalence of models, or the paper's
  translation/verification properties. JSON or D1 compatibility alone is not
  proof that two architecture representations are equivalent.
- **Source:** <https://arxiv.org/abs/2302.03503v2>

#### 2601.07301v1 — Engineering Decisions in MBSE: Insights for a Decision Capture Framework Development

- **Year:** 2026
- **Categories:** `cs.SE`
- **Classification:** **precedent** for decision context, **neighbor** for the
  MBSE implementation boundary
- **Theme:** decision capture, alternatives, requirements, behaviors, model
  slices
- **Why it matters to Mathen:** The paper directly addresses why decisions are
  hard to reuse when context is missing and proposes linking alternatives to
  requirements, behaviors, and architectural elements. This aligns with
  Mathen's claim/scope/provenance and negative-knowledge concerns.
- **Likely Mathen use:** Use its decision-context vocabulary when refining
  evidence links, alternatives, rationale, affected elements, and rejected
  options. Preserve decision uncertainty and context instead of flattening a
  decision into a timeless label.
- **Explicit non-claims:** Mathen must not claim to originate contextual
  decision capture, model slices, or the reported engineering framework. The
  paper's simplified example does not validate Mathen's cross-system corpus or
  its repository observation workflow.
- **Source:** <https://arxiv.org/abs/2601.07301v1>

### LLMs and software architecture

#### 2505.16697v1 — Software Architecture Meets LLMs: A Systematic Literature Review

- **Year:** 2025
- **Categories:** `cs.SE`
- **Classification:** **precedent** for landscape framing; **contrast** for
  Mathen's evidence-bounded scope
- **Theme:** LLM architecture tasks, automation, prompting, evaluation
- **Why it matters to Mathen:** This review maps LLM use across architecture
  tasks such as decision classification, pattern detection, and design
  generation, and exposes uneven evaluation coverage. It is the most direct
  supplied source for avoiding broad “LLMs for architecture” claims.
- **Likely Mathen use:** Use its task taxonomy to separate extraction,
  retrieval, classification, generation, conformance, and evaluation. Position
  any future Mathen LLM feature as a bounded assistant around evidence, not as
  an unqualified architecture authority.
- **Explicit non-claims:** Mathen must not claim to be the first LLM-assisted
  architecture system, to outperform the approaches surveyed, or to close all
  gaps identified by the review. This internal map is not a replacement for the
  review's systematic method.
- **Source:** <https://arxiv.org/abs/2505.16697v1>

### Knowledge-driven multi-agent design and agentic AKM

#### 2503.20536v1 — Knowledge-Based Multi-Agent Framework for Automated Software Architecture Design

- **Year:** 2025
- **Categories:** `cs.SE`
- **Classification:** **neighbor**
- **Theme:** knowledge-based agents, architecture-design roles, multi-source
  knowledge
- **Why it matters to Mathen:** MAAD explicitly proposes agents empowered by
  existing system designs, authoritative literature, and experts. This is
  directly relevant to the boundary between a knowledge substrate and a design
  generator.
- **Likely Mathen use:** Use the source separation as a checklist for future
  synthesis experiments: identify which claims came from reviewed cards,
  literature, or expert input, and preserve their provenance and confidence.
  Treat agent roles as orchestration hypotheses, not as evidence guarantees.
- **Explicit non-claims:** Mathen must not claim multi-agent architecture
  design, full automation, or the proposed framework's performance. A
  knowledge base that supports synthesis is not itself an autonomous designer.
- **Source:** <https://arxiv.org/abs/2503.20536v1>

#### 2507.21382v1 — MAAD: Automate Software Architecture Design through Knowledge-Driven Multi-Agent Collaboration

- **Year:** 2025
- **Categories:** `cs.SE`, `cs.AI`
- **Classification:** **neighbor**
- **Theme:** analyst/modeler/designer/evaluator agents, quality attributes,
  architecture blueprints
- **Why it matters to Mathen:** This related MAAD work operationalizes a
  multi-agent workflow with explicit roles and quality-attribute evaluation.
  It is useful prior art for separating discovery, modeling, synthesis, and
  evaluation rather than treating one generation step as the whole process.
- **Likely Mathen use:** Use its role decomposition as a comparison point for
  Mathen's discovery-versus-synthesis boundary and for designing experiments
  that record evaluator inputs, alternatives, and unresolved conflicts.
- **Explicit non-claims:** Mathen must not claim to reproduce MAAD's case
  studies, industrial feedback, model comparisons, or quality of generated
  blueprints. Role names do not establish a valid evidence or review protocol.
- **Source:** <https://arxiv.org/abs/2507.21382v1>

#### 2602.04445v1 — AgenticAKM: Enroute to Agentic Architecture Knowledge Management

- **Year:** 2026
- **Categories:** `cs.SE`
- **Classification:** **neighbor** and important **prior art**
- **Theme:** extraction, retrieval, generation, validation agents, ADR recovery
- **Why it matters to Mathen:** AgenticAKM decomposes architecture recovery and
  documentation into specialized extraction, retrieval, generation, and
  validation stages, and evaluates ADR generation across repositories. This is
  close prior art for the discovery/synthesis distinction and for an experiment
  loop around repository evidence.
- **Likely Mathen use:** Compare Mathen's deterministic observation and review
  boundaries with the proposed agent stages. Borrow the requirement to measure
  outputs across repositories while retaining explicit source evidence,
  rejection reasons, and claim types.
- **Explicit non-claims:** Mathen must not claim to be the first agentic AKM
  workflow, first automated ADR generator, or first multi-stage extraction /
  validation pipeline. The reported user study and repository results are not
  Mathen results and must not be silently transferred to Mathen.
- **Source:** <https://arxiv.org/abs/2602.04445v1>

#### 2601.19548v1 — From Scattered to Structured: A Vision for Automating Architectural Knowledge Management

- **Year:** 2026
- **Categories:** `cs.SE`
- **Classification:** **neighbor** and important **prior art**
- **Theme:** heterogeneous artifact extraction, linking, inconsistency,
  structured knowledge base, RAG
- **Why it matters to Mathen:** The vision of extracting and linking
  requirements, diagrams, code, and documentation, then checking inconsistency
  and enabling impact analysis, overlaps strongly with Mathen's evidence graph
  and provenance goals.
- **Likely Mathen use:** Use it to test the boundaries of artifact identity,
  cross-artifact links, temporal inconsistency, and retrieval context. Mathen's
  narrower contribution should be stated as an evidence-bounded implementation
  and experiment surface, if supported, not as the first structured AKM vision.
- **Explicit non-claims:** Mathen must not claim to originate heterogeneous
  artifact extraction, unified AK schemas, inconsistency checking, impact
  analysis, or RAG for architectural knowledge. This vision does not by itself
  validate Mathen's implementation or its proposed gap.
- **Source:** <https://arxiv.org/abs/2601.19548v1>

### Benchmarks and evaluation

#### 2606.29520v1 — SAKE: Software Architectural Knowledge Evaluation Benchmark for Large Language Models

- **Year:** 2026
- **Categories:** `cs.SE`, `cs.AI`, `cs.DB`
- **Classification:** **neighbor** and **contrast**
- **Theme:** reproducible benchmark, expert-curated questions, architectural
  competency, model evaluation
- **Why it matters to Mathen:** SAKE makes architectural knowledge evaluation
  reproducible and stratifies competency by architectural categories and context
  lengths. It is a useful reminder that an evaluation claim needs a fixed task,
  corpus, scoring method, and released artifact.
- **Likely Mathen use:** Use benchmark discipline when evaluating retrieval,
  evidence grounding, claim classification, relation discovery, or synthesis.
  Define Mathen-specific tasks that require citing evidence and respecting
  scope, rather than borrowing multiple-choice accuracy as a proxy for system
  understanding.
- **Explicit non-claims:** Mathen must not claim a new LLM benchmark, SAKE
  compatibility, or that multiple-choice architectural knowledge predicts
  repository-level architecture analysis. SAKE scores cannot be presented as
  evidence that a Mathen card or composition is correct.
- **Source:** <https://arxiv.org/abs/2606.29520v1>

## Prior-art synthesis and Mathen boundary

The bounded set establishes substantial prior art for all broad components of
the project:

- Pattern and quality-attribute knowledge, decision support, architectural
  views, ADRs, and industry communication predate Mathen.
- Web and repository retrieval, multi-source architecture recovery, and
  ground-truth-oriented evaluation predate Mathen.
- Formal architecture definitions, model theory, design-space exploration,
  invariants, MBSE decision capture, and tool interoperability predate Mathen.
- LLM-assisted architecture tasks, knowledge-based multi-agent design, agentic
  AKM, heterogeneous artifact linking, and architecture benchmarks are active
  and explicit prior art in the supplied recent sources.

Accordingly, Mathen should describe its likely contribution—if later supported
by implementation and experiments—as an **evidence-bounded cross-system
microstructure and experiment workflow** that composes familiar ideas under
strict claims, scope, provenance, contracts, negative knowledge, reproducible
observation, and discovery/synthesis separation. That is a positioning
hypothesis, not a novelty result. A publication-grade novelty or related-work
claim requires a broader search, version verification, full-text reading,
citation tracing, and comparison with non-arXiv literature.

## Suggested future checks

These are research questions, not commitments to implement them in this task:

1. Can a reviewer trace every cross-system feature or relation to fixed-source
   evidence and distinguish fact, inference, hypothesis, and analogy?
2. Does retaining negative knowledge reduce repeated unsupported relation
   proposals or improve reviewer agreement?
3. Do retrieval and synthesis evaluations change when scope, version, and
   provenance are required in the answer?
4. Can a composition experiment report preserved properties, conflicts, and
   failed checks without implying a proof of compatibility?
5. Which observations remain reproducible across repository revisions, tool
   versions, and regenerated indexes?

## Reference list

The complete bounded source set is listed below in the same versioned form used
in the entries above:

1. [2005.08393v1](https://arxiv.org/abs/2005.08393v1) — *Capturing Software Architecture Knowledge for Pattern-Driven Design*.
2. [2309.11572v1](https://arxiv.org/abs/2309.11572v1) — *Architecture Knowledge Representation and Communication Industry Survey*.
3. [2103.11705v1](https://arxiv.org/abs/2103.11705v1) — *Exploring Web Search Engines to Find Architectural Knowledge*.
4. [2311.04643v1](https://arxiv.org/abs/2311.04643v1) — *Software Architecture Recovery with Information Fusion*.
5. [1909.06809v5](https://arxiv.org/abs/1909.06809v5) — *Architecture Definition in Complex System Design Using Model Theory*.
6. [1603.00636v1](https://arxiv.org/abs/1603.00636v1) — *Semi-Automated Design Space Exploration for Formal Modelling*.
7. [2302.03503v2](https://arxiv.org/abs/2302.03503v2) — *Tool interoperability for model-based systems engineering*.
8. [2505.16697v1](https://arxiv.org/abs/2505.16697v1) — *Software Architecture Meets LLMs: A Systematic Literature Review*.
9. [2503.20536v1](https://arxiv.org/abs/2503.20536v1) — *Knowledge-Based Multi-Agent Framework for Automated Software Architecture Design*.
10. [2507.21382v1](https://arxiv.org/abs/2507.21382v1) — *MAAD: Automate Software Architecture Design through Knowledge-Driven Multi-Agent Collaboration*.
11. [2601.07301v1](https://arxiv.org/abs/2601.07301v1) — *Engineering Decisions in MBSE: Insights for a Decision Capture Framework Development*.
12. [2606.29520v1](https://arxiv.org/abs/2606.29520v1) — *SAKE: Software Architectural Knowledge Evaluation Benchmark for Large Language Models*.
13. [2602.04445v1](https://arxiv.org/abs/2602.04445v1) — *AgenticAKM: Enroute to Agentic Architecture Knowledge Management*.
14. [2601.19548v1](https://arxiv.org/abs/2601.19548v1) — *From Scattered to Structured: A Vision for Automating Architectural Knowledge Management*.
