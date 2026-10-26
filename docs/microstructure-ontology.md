# Architecture microstructure ontology

The microstructure contract is a focused, additive first slice for describing
reusable architectural units without treating every unit as a system. Its
machine-readable contract is
[`schemas/architecture-microstructure.schema.json`](../schemas/architecture-microstructure.schema.json),
and the Python model and semantic validator are in
[`src/mathen/microstructures.py`](../src/mathen/microstructures.py).

## Scope and review boundary

Microstructures are standalone candidate knowledge documents. They do not
change, overwrite, or promote reviewed cards in `data/systems/`. A future
review workflow may attach a reviewed microstructure to a card, but this slice
does not make that relationship implicit.

Every claim carries the existing Mathen vocabulary:

- `fact`: directly supported by evidence;
- `inference`: an abstraction derived from supported facts;
- `hypothesis`: a proposed model that still requires validation;
- `analogy`: an explanatory comparison, not an equivalence.

`claim_status` and non-empty `evidence_ids` are required on the document and
on each modeled element. A valid document is therefore evidence-linked, but
validation is not proof of implementation behavior.

## Scale levels

`scale.level` distinguishes the unit being described:

| Level       | Meaning                                                                                 |
| ----------- | --------------------------------------------------------------------------------------- |
| `primitive` | A small operation, data object, or runtime capability treated as an architectural unit. |
| `mechanism` | A reusable way of producing a behavior from state, events, and operations.              |
| `subsystem` | A bounded cooperating group of mechanisms with an interface and lifecycle.              |
| `system`    | A deployable or independently operated architecture.                                    |
| `ecosystem` | Multiple systems and external actors connected by stated boundaries.                    |

The level is descriptive, not a quality ranking. `unit` and `description`
make the interpretation explicit when a term is ambiguous.

## Contract dimensions

Each document records state and events, operations, inputs and outputs,
preconditions and postconditions, invariants, boundaries, resource effects,
failure modes, and a validity scope. The scope explicitly includes systems,
versions, deployment origins, conditions, and exclusions. Deployment origins
are data, not hardcoded URLs or an assumption about where a system runs.

Operation references are checked against input, output, precondition, and
postcondition IDs. Event state references are checked against declared states;
element IDs are unique across the document. These checks catch malformed
cross-references without claiming that the described transition is executable
or formally verified.

## Example validation

```bash
uv run mathen validate-microstructures data/microstructures
```

The default directory is intentionally separate from `data/systems/` and
`data/drafts/`. Empty collections are allowed in this first slice so a review
can describe a narrow unit without inventing unsupported lifecycle details.
