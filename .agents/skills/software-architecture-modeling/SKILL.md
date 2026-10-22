---
name: software-architecture-modeling
description: Translate software systems, source code, design documents, papers, and benchmarks into evidence-backed architecture cards with reusable features, mathematical views, state models, invariants, and trade-offs. Use when analyzing a system such as Git, SQLite, DuckDB, Supabase, Firecracker, Kafka, Kubernetes, or when comparing or composing architecture patterns.
---

# Software Architecture Modeling

Translate implementations into structured architectural models without confusing analogy with proof.

## Operating principles

- Start with evidence. Prefer official design documents, papers, source code, tests, benchmarks, and operational reports.
- Extract observable facts before assigning mathematical terminology.
- Use several views when necessary; do not force a complete system into one mathematical structure.
- Label every claim as `fact`, `inference`, `hypothesis`, or `analogy`.
- Record assumptions, scope, benefits, costs, failure modes, and counterexamples.
- Treat originality as an open research question. Structural similarity is not proof of influence or novelty.
- Keep all generated documentation and card content in English.

## Workflow

### 1. Define the analysis target

State the system, version or time boundary, target workload, and question. Examples:

- How does Git preserve identity while allowing references to move?
- Which design choices make DuckDB suitable for embedded OLAP?
- Which existing boundaries are composed by Supabase?
- Which functionality does Firecracker remove to optimize microVM density?

Do not begin with a desired mathematical label. Let the evidence and question determine the model.

### 2. Collect and classify evidence

Create stable evidence IDs and record the URI, source kind, title, and relevant notes. Use these source kinds:

- `official-doc`
- `paper`
- `source-code`
- `experiment`
- `secondary`

Do not cite a search result as if it were primary evidence. Fetch and inspect the source, and summarize only claims supported by it.

### 3. Extract architecture features

For each feature, record:

- stable ID and human-readable name;
- category, such as `storage-model`, `execution-model`, `state-model`, `security-model`, or `deployment-model`;
- exact description;
- claim type;
- benefits and costs;
- evidence IDs.

Describe transferable structure, not merely product features. For example, use `embedded-process-execution` rather than `has-a-python-package`.

### 4. Add mathematical views

For each view, provide:

- `model`: the mathematical or formal-system candidate;
- `question`: the concrete question the model answers;
- `assumptions`: conditions under which the abstraction is valid;
- `claim_type`: usually `inference` or `hypothesis`;
- `evidence_ids`.

Useful candidate views include:

- algebraic data types and relational algebra for data models;
- graphs, DAGs, and partial orders for dependencies or causality;
- state machines and operational semantics for lifecycle behavior;
- monoids or compositional algebras for operations;
- semilattices and monotone systems for convergence;
- refinement, simulation, or bisimulation for transparent optimizations;
- probability, queueing, complexity, and cost models for non-functional behavior.

Never call a structure a group, lattice, category, or homomorphism unless the required operations, laws, and domains have been stated. When the mapping is explanatory only, use `analogy`.

### 5. Record state and invariants when relevant

Define state components, transitions, preconditions, postconditions, and invariants. Distinguish clearly between an implementation guarantee, a model assumption, an observed empirical behavior, and an unverified conjecture.

### 6. Model composition and innovation

When comparing systems, identify reused primitives, changed abstraction boundaries, new constraints or target workloads, preserved properties, conflicts introduced by composition, and new trade-offs.

Use language such as “composes”, “adapts”, “reuses”, or “is structurally analogous to”. Do not claim that a system copied a design without historical evidence.

### 7. Validate and emit

Emit a card conforming to `schemas/architecture-card.schema.json` when working in this repository. Run:

```bash
uv run mathen validate
```

Before accepting a card, verify that all referenced evidence IDs exist, trade-offs reference known features, and every mathematical view has a question and assumptions. Put unresolved issues in the analysis response rather than hiding them in confident prose.

## Output requirements

For a short analysis, provide:

1. one-sentence system summary;
2. three to seven reusable architecture features;
3. one or more mathematical views with assumptions;
4. key trade-offs;
5. evidence and confidence;
6. unresolved questions.

For repository work, write the machine-readable card and update the relevant English documentation. Keep product-specific facts separate from transferable feature definitions.

See [`references/modeling-patterns.md`](references/modeling-patterns.md) for the detailed feature and mathematical-view vocabulary.
