# Scope-context pilot: MTH-0151

This pilot applies the evidence-bounded `scope_context` contract to seven
reviewed cards: SQLite, PostgreSQL, Kubernetes, Apache Kafka, AWS Firecracker,
Apache Airflow, and CarryCtx.

## Boundary

Only card-level metadata was added. Features, mathematical views, evidence
records, drafts, and graph relations were not edited. Every specified
dimension cites evidence already local to its card. The metadata records
documented architecture boundaries; it is not a benchmark and does not claim
measured performance, capacity, production failure rates, or universal
validity.

The pilot deliberately leaves `scale` unspecified for all seven cards. It also
leaves `failure_conditions` unspecified for Kubernetes, Firecracker, and
Airflow because the current card evidence does not provide a bounded failure
or recovery condition suitable for this contract. These are absence-of-record
states, not negative findings.

## Coverage

| Dimension          | Specified | Unknown | Unspecified | Not applicable |
| ------------------ | --------: | ------: | ----------: | -------------: |
| Validity scope     |         7 |       0 |           0 |              0 |
| Workload           |         7 |       0 |           0 |              0 |
| Runtime conditions |         7 |       0 |           0 |              0 |
| Scale              |         0 |       0 |           7 |              0 |
| Failure conditions |         4 |       0 |           3 |              0 |

`specified` here means that the cited official documentation or fixed source
revision states the boundary. It does not turn a feature or mathematical view
into a stronger claim, and the scope metadata uses `claim_type=fact` only for
the bounded scope statement itself.

## Follow-up

The next evidence task should add detached, reproducible observation records
for a small number of experiments. Those records—not this documentation-only
pilot—should establish workload, scale, runtime configuration, failure
conditions, measurements, and limitations.
