# MTH-0197: SQLite busy/timeout observation

MTH-0197 records a bounded local SQLite lock-contention observation. It is
research-only evidence and remains detached from the canonical SQLite card.
The observation and finite state-machine candidate are `canonical: false` and
`under-review`; neither is a general SQLite claim.

## Protocol and oracle

The runner is
[`scripts/g5_sqlite_busy_timeout_experiment.py`](../scripts/g5_sqlite_busy_timeout_experiment.py).
It uses the locally available SQLite source ID
`4d8adfb30e03f9cf27f800a2c1ba3c48fb4ca1b08b0f5ed59a4d5ecbf45e20a3`, Python
3.13.13, SQLite 3.50.4, and a fixed four-row seed. Each repetition creates a
fresh database and performs this sequence:

1. Commit the fixed seed using SQLite's default journal and synchronous settings.
2. On a holder connection, begin `BEGIN IMMEDIATE`, insert the fifth row, and
   leave the transaction uncommitted.
3. On a second connection with `timeout=0.0`, attempt `BEGIN IMMEDIATE`. The
   bounded failure oracle is the exact `sqlite3.OperationalError` message
   `database is locked`.
4. Commit the holder, read the committed state from the contender, close both
   connections, reopen the database, and run `PRAGMA integrity_check`.
5. Compare every observation across three repetitions.

The observed result was three lock failures, a five-row committed state after
release and reopen, successful integrity checks, and equal raw observations in
all three repetitions. Timing is deliberately not measured; the observation
records a null timing measurement with `not-measured` status.

## Artifacts

- [`g5-sqlite-busy-timeout-results-mth-0197.json`](../data/experiments/g5-sqlite-busy-timeout-results-mth-0197.json)
  contains the raw per-repetition results and runner digest.
- [`g5-sqlite-busy-timeout-observation-mth-0197.json`](../data/experiments/g5-sqlite-busy-timeout-observation-mth-0197.json)
  is the detached v1 observation contract with source/result digests, scope,
  review state, null timing, and explicit exclusions.
- [`sqlite-busy-timeout-mth-0197.json`](../data/mathviews/sqlite-busy-timeout-mth-0197.json)
  is an optional finite state-machine candidate. Its deterministic checks only
  establish that the declared finite transitions are closed and have an initial
  state.

## Boundary

This protocol does **not** establish general concurrency behavior, busy-handler
or timeout policy, compatibility, performance, durability, crash recovery,
power-loss behavior, checkpoint behavior, causality beyond the scripted local
sequence, or architecture superiority. It does not test nonzero timeout values,
alternate journal modes, multiple writers beyond the two local connections,
process crashes, power loss, or a distributed/deployed environment. The
absence-of-evidence record in the mathview is not a negative finding.

The protocol does not modify canonical cards, drafts, API, MCP, D1 migrations,
relations, production resources, or paper files.

## Reproduction

```bash
uv run --offline python scripts/g5_sqlite_busy_timeout_experiment.py \
  --expected-source-id \
  4d8adfb30e03f9cf27f800a2c1ba3c48fb4ca1b08b0f5ed59a4d5ecbf45e20a3 \
  --repetitions 3 \
  --output data/experiments/g5-sqlite-busy-timeout-results-mth-0197.json \
  --observation-output data/experiments/g5-sqlite-busy-timeout-observation-mth-0197.json
```

The command must be run with the same SQLite source ID. A different build is a
different experiment and must not overwrite these recorded results.
