# Modeling Methodology

## 1. Extract before interpreting

Start from primary evidence: official design documents, papers, source code,
benchmarks, and operational reports. Extract observable facts before assigning
mathematical terminology.

## 2. Use multiple mathematical views

The following mappings are useful starting points, not mandatory labels:

| Architecture question           | Candidate view                            |
| ------------------------------- | ----------------------------------------- |
| What are the data and objects?  | Sets, types, algebraic data types         |
| How are objects related?        | Graphs, DAGs, partial orders              |
| How does the system evolve?     | State machines, transition systems        |
| Which operations compose?       | Monoids, algebras, categories             |
| Does state converge?            | Semilattices, monotone systems            |
| Is an optimization transparent? | Refinement, simulation, bisimulation      |
| How do failures affect service? | Probability, queueing, reliability models |
| How are resources bounded?      | Complexity and cost models                |

Every mathematical view must include a `question` and `assumptions`. A label
without a corresponding definition or use is not a useful feature.

## 3. Separate claim types

Each statement should be classified as one of:

- `fact`: directly supported by evidence;
- `inference`: a reasonable abstraction derived from facts;
- `hypothesis`: a proposed model requiring validation;
- `analogy`: an explanatory comparison that is not a formal equivalence.

Only `fact` claims should be presented as implementation guarantees. A model
can be mathematically elegant and still fail to describe an edge case of the
real implementation.

## 4. Record trade-offs as first-class data

Every feature should state its expected benefits, costs, preconditions, and
failure modes. For example, embedded execution may reduce deployment and IPC
overhead while coupling the system lifetime to the host process and reducing
process-level isolation.

## 5. Validate in layers

Validation should progress from cheap to expensive:

1. JSON Schema validation;
2. semantic consistency checks;
3. source and citation review;
4. executable examples or property tests;
5. benchmarks, fault injection, or model checking where applicable.

## 6. Repository analysis stages

Repository analysis is deliberately staged:

1. resolve a repository ref to a commit;
2. record reproducible source provenance;
3. extract deterministic observations such as tracked paths, language counts,
   build markers, and weak path-level signals;
4. use those observations to prioritize source and documentation review;
5. ask an LLM to propose semantic features and mathematical views;
6. review and validate the resulting draft before promotion.

Tree statistics and path signals are evidence for navigation, not architecture
claims. A source archive is sufficient for tree inspection but does not preserve
history-sensitive evidence; use a Git checkout when commit history or blame is
part of the question.

## Architecture Card contract

The machine-readable contract lives in
[`schemas/architecture-card.schema.json`](../schemas/architecture-card.schema.json).
The examples in `data/systems/` intentionally contain both facts and
inferences so that later tooling can distinguish them.
