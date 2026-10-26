# MTH-0153 lifecycle-status pilot

**Status:** Evidence-bounded canonical pilot; no production/API/D1 changes.

This pilot adds explicit lifecycle metadata to exactly seven canonical cards:
`sqlite`, `postgresql`, `kubernetes`, `kafka`, `firecracker`, `airflow`, and
`carryctx`. The machine-readable audit is
`docs/audits/lifecycle-status-pilot-mth-0153.json`; rerun it with:

```bash
uv run python scripts/audit_lifecycle_status.py data/systems --pilot
```

## Selection and counts

| Surface | Selected records | `observed` | `proposed` | Unknown/not recorded |
| --- | ---: | ---: | ---: | ---: |
| Features | 39 | 7 | 0 | 32 |
| Mathematical views | 28 | 0 | 7 | 21 |
| **All selected records** | **67** | **7** | **7** | **53** |

The pilot writes 14 lifecycle objects: one directly documented feature and one
bounded candidate mathematical view per selected card. The lifecycle
`claim_status` remains independent (`under-review` for observed feature
assertions and `proposed` for candidate views); no owning feature or view claim
was promoted.

## Evidence-bounded selections

- **`sqlite`**
  - Feature: `journal-based-atomic-commit`
    (`sqlite-atomic-commit`).
  - View: `Crash-recovery transition system`
    (`sqlite-atomic-commit`, `sqlite-wal`).
- **`postgresql`**
  - Feature: `transaction-scoped-retry-boundary`
    (`postgresql-transaction-isolation`).
  - View: `Session and process transition system`
    (`postgresql-architecture`).
- **`kubernetes`**
  - Feature: `controller-reconciliation-loops`
    (`kubernetes-controller-doc`, `kubernetes-controller-source`).
  - View: `Distributed feedback control system`
    (`kubernetes-controller-doc`, `kubernetes-controller-source`).
- **`kafka`**
  - Feature: `retained-replayable-events` (`kafka-introduction`).
  - View: `Replayable event transition system` (`kafka-introduction`).
- **`firecracker`**
  - Feature: `minimal-machine-model` (`firecracker-design`).
  - View: `Layered isolation boundary` (`firecracker-design`).
- **`airflow`**
  - Feature: `dag-dependency-graph`
    (`airflow-architecture-doc`, `airflow-source-commit`).
  - View: `DAG readiness relation`
    (`airflow-architecture-doc`, `airflow-source-commit`).
- **`carryctx`**
  - Feature: `guarded-task-lifecycle`
    (`carryctx-task-source`, `carryctx-lifecycle-doc`).
  - View: `Guarded project lifecycle transition system`
    (`carryctx-task-source`, `carryctx-lifecycle-doc`).

## Explicit absence-of-evidence boundaries

- The other 32 features and 21 mathematical views in the seven selected cards
  intentionally omit lifecycle metadata. Omission means **unknown/not
  recorded**, not proposed, observed, reviewed, current, or absent.
- Cards outside the seven-card allowlist were not edited. Drafts, relations,
  production resources, migrations, API contracts, and claims were not
  promoted or changed.
- No lifecycle status was inferred from `claim_type`, `claim_status`, evidence
  kind, popularity, graph degree, version, name/category, or similarity.
- `observed` is bounded to the named official documentation/source evidence and
  its stated revision or observation boundary; it does not assert universal
  currentness.
- `proposed` marks a candidate mathematical lifecycle view only. It does not
  establish a formal proof, implementation-wide validation, compatibility,
  convergence, isolation, replay, or substitutability.
- No `reviewed`, `deprecated`, or `superseded` status is asserted. The cited
  records do not provide the independent review, direct deprecation, or direct
  replacement evidence required by the lifecycle contract.

The report is deterministic and read-only: `mutation_performed` is `false`,
the selected-card allowlist is fixed, statuses and evidence IDs are sorted in
stable order, and unsupported records remain visible as unknown/not recorded.
