# Cross-domain structural analogy mappings

Mathen stores cross-domain comparisons as standalone, versioned analogy
mappings. The machine-readable contract is
[`schemas/cross-domain-analogy.schema.json`](../schemas/cross-domain-analogy.schema.json)
and the semantic validator/model is
[`src/mathen/analogies.py`](../src/mathen/analogies.py).

## Review boundary

An analogy mapping is a candidate abstraction, not a canonical graph relation.
It is intentionally separate from `data/systems/`, card `relations`, and
feature relations. A mapping must identify:

- source and target domains and concepts;
- mapping type and source/target scale;
- shared and preserved properties, with boundaries;
- explicitly non-preserved properties;
- version, condition, exclusion, and configurable deployment scope;
- at least one counterexample;
- claim type/status and local evidence IDs for every claim; and
- an explicit non-equivalence statement and substitutability decision.

The document-level claim type is always `analogy`. The validator rejects
unknown local evidence and dangling concept references. It does not infer
canonical relations, causal mechanisms, formal equivalence, proof, dependency,
composition, substitutability, or historical influence. Historical influence
requires a separate directly evidenced claim.

## Example

`data/analogies/chemistry-biology.json` compares reaction-network and
gene-regulatory motifs. It preserves only a bounded graph-level resemblance;
it explicitly excludes parameter transfer and mechanistic equivalence.

Validate the fixture collection with:

```bash
uv run mathen validate-analogies data/analogies
```

Deployment origins are values in `scope.deployment_origins`, not hardcoded
hosts. They describe where the comparison is applicable or was evaluated and
must remain configurable by the author/reviewer.
