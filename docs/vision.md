# Vision

## Problem

Software architecture knowledge is usually stored as prose, diagrams, source
code, and isolated papers. That makes it difficult to compare systems by
transferable structure or to search for combinations of design properties.

Mathen explores an intermediate representation between implementation and
natural-language documentation. The representation records architecture
claims in a form that can be reviewed by engineers, mapped to mathematical
models, and later queried by tools.

## Working hypothesis

A software system can be modeled through several complementary views:

```text
system
├── data model
├── state space
├── operations and transitions
├── dependency and causality graph
├── consistency and convergence model
├── storage and execution model
├── failure model
├── resource and performance model
└── evolution and migration model
```

No single mathematical structure is expected to explain an entire system. A
mathematical view is useful only when it answers a concrete question and lists
its assumptions.

## Role of an LLM

An LLM can propose abstractions from source code, design documents, papers,
and experiments. It should not silently turn those proposals into facts. The
pipeline must preserve:

- source evidence;
- the exact claim;
- assumptions and scope;
- confidence;
- counterexamples or unresolved questions;
- human or tool review status.

The intended workflow is therefore:

```text
evidence → candidate claims → architecture card → review → knowledge graph
```

## What counts as innovation

The project does not assume that new systems are built from isolated “best
features”. A useful record should explain the composition boundary, the new
constraints, the preserved properties, and the new trade-offs introduced by
the combination.
