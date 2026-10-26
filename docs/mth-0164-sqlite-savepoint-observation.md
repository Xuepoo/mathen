# MTH-0164: SQLite savepoint partial rollback observation

MTH-0164 records a third, non-duplicate SQLite observation. MTH-0152 covered an
explicit full-transaction rollback after a constraint failure, while MTH-0156
covered reader visibility across a WAL writer commit. This protocol instead
asks whether rollback to a savepoint removes only the inner work while an outer
transaction remains committable.

## Protocol and boundary

The runner is
[`scripts/g5_sqlite_savepoint_experiment.py`](../scripts/g5_sqlite_savepoint_experiment.py).
It verifies SQLite source ID before writing, records the complete Python/OS/
SQLite environment, uses only the standard library, and repeats a fixed
protocol three times:

1. Create a fresh database and commit four fixed records.
2. Begin an outer transaction and insert `(5, epsilon, 50)`.
3. Create a savepoint and insert `(6, zeta, 60)`.
4. Roll back to and release the savepoint; compare the complete ordered rows.
5. Commit the outer transaction, run `PRAGMA integrity_check`, close/reopen,
   and compare the complete rows and all repetitions.

The observed result is bounded: the six-row inner state returned to five rows,
the fifth row remained after the outer commit, and five rows were visible after
reopen in all three repetitions. This is distinct from MTH-0152's explicit
full-transaction rollback and MTH-0156's two-connection WAL snapshot protocol.
It does not test WAL reader snapshots, full-transaction rollback, concurrent
writers, nested savepoint contention, process crash, power loss, durability,
or performance. Timing is deliberately not measured; the observation uses a
null measurement with `not-measured` status rather than treating missing timing
as zero.

## Artifacts

- [`g5-sqlite-savepoint-observation-mth-0164.json`](../data/experiments/g5-sqlite-savepoint-observation-mth-0164.json)
  is the detached v1 observation contract. It is unreviewed research evidence
  with `canonical: false`, explicit scope, provenance, artifact digests, and
  local evidence closure.
- [`g5-sqlite-savepoint-results.json`](../data/experiments/g5-sqlite-savepoint-results.json)
  contains all raw per-repetition observations and the runner digest.
- [`sqlite-savepoint-partial-rollback-mth-0164.json`](../data/mathviews/sqlite-savepoint-partial-rollback-mth-0164.json)
  is a standalone finite state-machine candidate. Its deterministic classifier
  validates initial-state and transition-closure checks; its validation records
  report the bounded observation and abstain from claims about omitted
  conditions.

These are research-only artifacts. The task does not modify `data/systems/`,
drafts, relations, API/migrations, MCP, web, production resources, or paper
files.

## Reproduction and checks

```bash
uv run --offline python scripts/g5_sqlite_savepoint_experiment.py \
  --expected-source-id \
  4d8adfb30e03f9cf27f800a2c1ba3c48fb4ca1b08b0f5ed59a4d5ecbf45e20a3 \
  --repetitions 3 \
  --output data/experiments/g5-sqlite-savepoint-results.json
```

The runner writes the raw result only after all expected states and repetition
comparisons pass. Focused tests validate the detached observation through the
existing card validator, validate the standalone math view, and check the
partial-rollback transition. The recorded result is not a canonical card claim.
