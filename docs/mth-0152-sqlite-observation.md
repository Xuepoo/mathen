# MTH-0152: SQLite observation and mathematical-view validation

MTH-0152 re-runs the existing G5 SQLite transaction protocol and records the
result as a version-1 observation. The run is stored separately from the
canonical card payload and remains `canonical: false`; the SQLite card cites it
as local research evidence so the evidence and validation records have a
closed reference boundary.

## Observed protocol

The runner uses SQLite source ID
`4d8adfb30e03f9cf27f800a2c1ba3c48fb4ca1b08b0f5ed59a4d5ecbf45e20a3`, a fixed
four-row dataset, one connection, SQLite's default journal and synchronous
settings, and three repetitions. Each repetition commits the seed rows,
inserts a fifth row followed by a duplicate primary key, explicitly rolls back
after `IntegrityError`, commits the fifth row in a new transaction, runs
`PRAGMA integrity_check`, and verifies the rows after close/reopen.

The run observed:

- rollback preserved 4 rows and sum 100 in all 3 repetitions;
- the subsequent commit produced 5 rows and sum 150;
- all 3 integrity checks returned `ok`;
- all 3 rollback checks passed;
- all repetitions produced the same observations.

The exact observation object is
`data/experiments/g5-sqlite-transaction-mth-0152-observation.json`, and the raw
runner result is
`data/experiments/g5-sqlite-transaction-mth-0152-results.json`.

## Mathematical boundary

`data/mathviews/sqlite-crash-recovery-transition-system-mth-0152.json` models
the bounded state sequence `seeded -> transaction-failed -> rolled-back ->
recovered -> reopened`. Its `observed-result` record supports only the explicit
application rollback and subsequent close/reopen behavior under this protocol.

Its `absence-of-evidence` record makes the boundary explicit: the run did not
test process crashes, power loss, automatic recovery after interruption,
concurrent writers, alternate durability modes, or performance. It therefore
does not establish a general atomicity, durability, or crash-recovery theorem.
