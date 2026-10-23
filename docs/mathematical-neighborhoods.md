# Mathematical neighborhoods

The model-neighborhood graph is a navigational projection over reviewed
mathematical views. It helps readers find systems whose authors described them
with related model vocabulary, while retaining the original view metadata and
source-local evidence IDs.

## API shape

`GET /api/graph/models` returns the usual API envelope:

```json
{
  "data": {
    "nodes": [
      { "id": "system-id", "name": "System", "type": "system" },
      {
        "id": "model:state-transition-systems",
        "name": "State and transition systems",
        "type": "model"
      }
    ],
    "edges": [
      {
        "source": "system-id",
        "target": "model:state-transition-systems",
        "type": "modeled-by",
        "claim_type": "inference",
        "metadata": [
          {
            "id": 1,
            "model": "Process lifecycle state machine",
            "question": "How does execution transition?",
            "assumptions": ["..."],
            "claim_type": "inference",
            "evidence_ids": ["source-local-id"]
          }
        ]
      }
    ]
  }
}
```

Each system/model pair has one edge. Multiple views are aggregated in that
edge's `metadata` list. The edge's `claim_type: inference` describes only the
classification/grouping operation; each view keeps its own original
`claim_type`. Evidence IDs are copied from the view and remain local to its
source card.

## Conservative families

The classifier uses bounded phrases in the stated model name. Current family
hubs include:

- State and transition systems
- Graphs and partial orders
- Algebra and relational algebra
- Queueing, cost, and resource models
- Lattices and convergence
- Simulation and refinement
- Types and grammars
- Dataflow and pipelines
- Probabilistic and stochastic models
- Optimization and scheduling

Rules prefer specific mathematical phrases and do not infer a family from
generic words such as `boundary` or `graph` alone. For example, a
`commutative algebra` view is grouped with algebra, a queueing cost model is
grouped with queueing/cost/resource models, and a refinement view is grouped
with simulation/refinement. A name that does not match a bounded rule gets a
stable, unique model node so that the reviewed view is still discoverable.

## Interpretation boundary

These hubs are not dependency edges, equivalence claims, proofs, historical
influence claims, or evidence that two systems can be composed. They express a
curated navigational inference over author-labelled views. Readers must inspect
the question, assumptions, original claim type, and source-local evidence
before making a stronger interpretation.
