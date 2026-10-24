<!-- markdownlint-disable MD013 -->

# Mathen as a research instrument

Mathen is intended to study how software architecture can be explored across
domains, not to ask an LLM to generate a final architecture from a familiar
template. This document records the current research position and the
questions that still require evidence. It is a research hypothesis and design
direction, not a claim that the full loop has already been validated.

## The human–LLM complement

Human researchers and language models contribute different capabilities:

| Participant            | Primary contribution                                                                            | Boundary                                                                                               |
| ---------------------- | ----------------------------------------------------------------------------------------------- | ------------------------------------------------------------------------------------------------------ |
| Human researcher       | Problem reframing, curiosity, unusual questions, research direction, and final review           | Human insight is difficult to scale and is not automatically reproducible                              |
| LLM                    | Broad cross-domain retrieval, local explanation, candidate abstractions, and candidate mappings | Output follows prompts and available evidence; it is not proof, a theorem, or an engineering guarantee |
| Graph analysis         | Communities, centrality, paths, bridges, and structural positions                               | A graph metric describes the current projection, not intrinsic importance or truth                     |
| Vector retrieval       | Semantic recall, terminology alignment, and distant candidate discovery                         | Similarity is a candidate signal, not a typed relation or compatibility result                         |
| Mathematical contracts | Deterministic checks, assumptions, laws, scope, and property classifications                    | A finite check validates the supplied model data, not the entire implementation                        |
| Experiments            | Runtime behavior, counterexamples, failure modes, and new evidence                              | An experiment has a workload and scope; it does not automatically generalize                           |

The intended division of labor is:

```text
human question and reframing
              ↓
graph/vector candidate discovery
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
[`llm-modeling.md`](llm-modeling.md), and the current decision is recorded in
CarryCtx as `DEC-0003`.

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

## Current status and related work

The repository already contains the first pieces of this direction:

- evidence-bounded LLM protocol and secret-safe provenance sidecars;
- scale-aware architecture microstructure contracts;
- checkable mathematical-view contracts;
- explicit cross-domain analogy mappings with non-equivalence and
  counterexamples;
- bounded composition candidates that remain `proven: false`;
- read-only graph/API/MCP boundaries.

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
