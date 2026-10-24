# Checkable mathematical architecture-view contracts

`schemas/architecture-mathematical-view.schema.json` defines the versioned
(`schema_version: "1.0"`) contract for turning a descriptive
`mathematical_views` label into an evidence-bounded candidate model. The
semantic validator and deterministic classifier are in
`src/mathen/mathviews.py`; a card may embed one under
`mathematical_views[].contract`. The field is additive, so existing labels
without a contract remain valid.

## Required boundary

Every contract records:

- a finite or explicitly described **carrier** and, where applicable, a
  **state space**;
- **operations**, **relations**, and **transitions** using IDs and closed
  references;
- named **laws_or_checks** and a deterministic `classification` of `valid`,
  `invalid`, or `undetermined`;
- assumptions, a version/system/deployment-origin **validity_scope**;
- `claim_type`, `claim_status`, and non-empty local `evidence_ids`.

Evidence IDs must exist in the containing Architecture Card when the contract
is embedded. A contract can be `valid` only because its supplied finite data
passes the defined checks. This is not a proof that the implementation has the
modeled semantics. Missing observations or an uncheckable infinite model must
remain `undetermined`; a failed law is `invalid`. `analogy` and `hypothesis`
are permitted claim types and do not become facts because a classifier returns
`valid`.

## Family templates

| Family                     | Carrier/state and required check                                                                                                                                       |
| -------------------------- | ---------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| `graph`                    | Carrier vertices and a relation of ordered pairs; checks closure of the relation.                                                                                      |
| `dag`                      | Directed graph relation; deterministic cycle detection must pass.                                                                                                      |
| `partial_order`            | Carrier and relation; reflexivity, antisymmetry, and transitivity must pass.                                                                                           |
| `state_machine`            | `state_space` with initial/terminal states and labeled transitions closed over it; at least one initial state is required.                                             |
| `algebraic`                | Operations with arity and, for checkable finite candidates, a closed operation table; declared associativity, commutativity, idempotence, or closure laws are checked. |
| `semilattice`              | A finite binary operation table; associative, commutative, and idempotent laws are all required and checked.                                                           |
| `monotone_system`          | An algebraic carrier plus a declared order relation and monotonicity checks; insufficient order/function tables remain undetermined.                                   |
| `refinement`, `simulation` | Two transition systems, a relation of state pairs, and forward transition obligations.                                                                                 |
| `bisimulation`             | The simulation obligations in both directions.                                                                                                                         |
| `cost`, `complexity`       | Finite numeric cost or growth parameters; parameters must be finite and non-negative.                                                                                  |
| `queueing`                 | `arrival_rate` and positive `service_rate`; the deterministic single-server stability check requires utilization below 1.                                              |
| `reliability`              | Finite probability parameters; each must lie in `[0, 1]`.                                                                                                              |

The implementation intentionally does not infer laws from prose. For example,
calling a dependency graph a DAG does not make it one: a cycle is a
deterministic `invalid` result. Calling a system a semilattice without a
finite binary operation table is `undetermined`, not valid.

## Standalone validation

Standalone contract files can be validated individually or as a directory:

```bash
uv run mathen validate-mathviews tests/fixtures/math-view-valid.json
uv run mathen validate-mathviews data/mathviews
```

The command uses the same loader and semantic validator as embedded contracts.
It scans only top-level `*.json` files in a directory, reports each valid path,
and treats an absent or empty directory as a successful no-op. Standalone
contracts validate their own non-empty `evidence_ids`; card-local evidence
boundaries are checked when a contract is embedded in an Architecture Card.

## Partial, observational, and temporal scope

Contracts may describe only an observational projection: put the observation
boundary in `assumptions` and the omitted implementation behavior in
`validity_scope.exclusions`. `validity_scope.versions` and
`deployment_origins` are required so the same mathematical label is not
silently applied to every release or deployment. A partial carrier must say
that it is partial in the question or assumptions; absence of an element is
not evidence that the element cannot exist.

## LLM and card mapping

The modeling bundle advertises this contract as an optional replacement for a
plain view label:

| Existing view field                          | Contract field                                            |
| -------------------------------------------- | --------------------------------------------------------- |
| `model`                                      | `family`, carrier, operations, relations, and transitions |
| `question`                                   | `question`                                                |
| `assumptions`                                | `assumptions` plus validity exclusions                    |
| `claim_type`, `claim_status`, `evidence_ids` | same-named contract fields                                |

LLM output remains in `data/drafts/` and the existing research protocol and
human review boundary still apply. Automated validation never promotes or
overwrites `data/systems/`; it only detects malformed references and reports
bounded consistency outcomes.

Representative valid and invalid candidates are in
`tests/fixtures/math-view-valid.json` and
`tests/fixtures/math-view-invalid.json`.
