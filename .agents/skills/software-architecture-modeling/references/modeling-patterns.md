# Modeling Patterns

## Feature categories

Use the narrowest category that explains the design:

| Category            | Typical questions                                                  |
| ------------------- | ------------------------------------------------------------------ |
| `data-model`        | What objects, records, types, or relations exist?                  |
| `storage-model`     | How are data persisted, addressed, shared, and recovered?          |
| `execution-model`   | How are work units scheduled, interpreted, compiled, or batched?   |
| `state-model`       | What is mutable, immutable, derived, or externally controlled?     |
| `consistency-model` | What ordering, isolation, durability, or convergence is promised?  |
| `deployment-model`  | Which process, host, network, and lifecycle boundaries exist?      |
| `security-model`    | Where are trust, authorization, and isolation boundaries enforced? |
| `composition-model` | How are components combined and how do interfaces constrain them?  |
| `failure-model`     | Which failures are expected, detected, retried, or isolated?       |
| `resource-model`    | How are CPU, memory, I/O, network, and cost bounded?               |

## Mathematical view vocabulary

### Data and structure

- **Algebraic data type**: use for sum/product/recursive object models.
- **Relational algebra**: use for composable query and relation operators.
- **Graph or DAG**: use for dependencies, ancestry, scheduling, or provenance.
- **Partial order**: use only when reflexivity, antisymmetry, and transitivity are defined over the modeled relation.

### Behavior and change

- **Transition system**: use for states, actions, guards, and effects.
- **Operational semantics**: use when small-step or big-step rules clarify command behavior.
- **Event structure**: use for causality and conflict between concurrent events.
- **Monoid or algebraic action**: use when a closed composition law and identity, or an explicit action on a state, are defined.

### Consistency and optimization

- **Semilattice**: use for an associative, commutative, idempotent merge operation over a stated domain.
- **Monotone system**: use when state moves in a declared order and does not decrease.
- **Refinement or simulation**: use when a concrete implementation preserves abstract behavior under a defined abstraction map.
- **Bisimulation**: use only when both systems' transitions are related in both directions according to the stated relation.

## Common false equivalences

- A hash is not a mathematical injection over all byte strings. State a finite-domain or no-collision assumption.
- A merge base is not necessarily a unique meet. Multiple maximal common ancestors are possible.
- A successful patch application is not the same as semantic equivalence.
- A component composition is not automatically a categorical pushout.
- A performance optimization is not transparent without an abstraction function and an equivalence claim.
- A “single-threaded” system may still use background threads or multiple processes; define the scope precisely.

## Composition record

When claiming that a newer system combines older ideas, record a relation like:

```yaml
source_systems:
  - sqlite
  - postgresql
reused_features:
  - embedded-process-execution
  - database-enforced-access-control
changed_boundary: "Expose database capabilities as a managed application platform"
target_constraints:
  - low backend setup effort
  - direct SQL and extension compatibility
preserved_properties:
  - relational query semantics
new_tradeoffs:
  - platform complexity
  - centralized database dependency
evidence_status: "documented composition; originality not established"
```
